import os
import pandas as pd
import pickle
from fuzzywuzzy import fuzz
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
import requests
from bs4 import BeautifulSoup


MODEL_KNN_PICKLE = 'knn_pickle'
DATA_PICKLE = 'data_pickle'
MAPPER_PICKLE = 'mapper_pickle'
LINKS_PICKLE = 'links'
DATA_FOLDER = 'D:\\RecommenderSystem\\data'
CACHE_FOLDER = 'D:\\RecommenderSystem\\cache'
ANIME_FILENAME = 'anime-filtered.csv'
RATINGS_FILENAME = 'rating-filtered.csv'
popularity_thres = 50
ratings_thres = 50
NUM_OF_OUTPUT = 11
DEFAULT_IMG = '/images/default.png'


def _get_page_content(id):
	url = 'https://myanimelist.net/anime/' + str(id)
	headers = {'Content-Type': 'text/html', }
	try:
		page = requests.get(url, headers=headers)
		soup = BeautifulSoup(page.content, 'html.parser')
		results = soup.find(id='content')
		img_main = results.find_all('td', class_='borderClass')
		for el in img_main:
			link = el.find('img')['data-src']
			if link is None:
				return DEFAULT_IMG
			return link
	except Exception:
		return DEFAULT_IMG


def get_id_to_link_map(ids):
	map = {}
	try:
		map = pickle.load(open(os.path.join(CACHE_FOLDER, LINKS_PICKLE), 'rb'))
	except Exception:
		map = {}
	i = 0
	for id in ids:  # try to improve links
		if id[0] not in map or map[id[0]] == DEFAULT_IMG:
			try:
				link = _get_page_content(id[0])
				map[id[0]] = link
				print("Trying to improve links for " + str(id[0]) + "... result: " + link)
				if link != DEFAULT_IMG:
					i += 1
			except Exception:
				map[id[0]] = DEFAULT_IMG
				print("Error for " + str(id[0]))
		if i % 100 == 0:
			_save_pickle(links=map)
	_save_pickle(links=map)
	return map


def fuzzy_matching(mapper, fav_anime, verbose=True):
	match_tuple = []
	# get match
	for idx, title in mapper.items():
		ratio = fuzz.ratio(title[1][0].lower(), fav_anime.lower())
		if ratio >= 60:
			match_tuple.append((title, idx, ratio))
	match_tuple = sorted(match_tuple, key=lambda x: x[2])[::-1]
	if not match_tuple:
		print('Oops! No match is found')
		return
	if verbose:
		print('Found possible matches in our database: {0}\n'.format([x[0][1][0] for x in match_tuple]))
	return match_tuple[0][1]


def make_recommendation(model_knn, data, mapper, fav_anime, links):
	idx = fuzzy_matching(mapper, fav_anime, verbose=True)
	if not idx:
		return
	distances, indices = model_knn.kneighbors(data[idx], n_neighbors=NUM_OF_OUTPUT)
	raw_recommends = sorted(list(zip(indices.squeeze().tolist(), distances.squeeze().tolist())), key=lambda x: x[1])[:0:-1]
	rec_map = {}
	print('Recommendations for {}:'.format(fav_anime))
	for i, (idx, dist) in enumerate(raw_recommends):
		rec_map[mapper[idx][1][0]] = {'id': mapper[idx][0], 'dist': int(dist*100), 'img': links[mapper[idx][0]]}
		print(mapper[idx][1][0])
	print(rec_map.keys())
	return rec_map


def _save_pickle(data=None, mapper=None, links=None):
	if data is not None:
		data_pickle = open(os.path.join(CACHE_FOLDER, DATA_PICKLE), 'wb')
		pickle.dump(data, data_pickle)
		data_pickle.close()
	if mapper is not None:
		mapper_pickle = open(os.path.join(CACHE_FOLDER, MAPPER_PICKLE), 'wb')
		pickle.dump(mapper, mapper_pickle)
		mapper_pickle.close()
	if links is not None:
		links_pickle = open(os.path.join(CACHE_FOLDER, LINKS_PICKLE), 'wb')
		pickle.dump(links, links_pickle)
		links_pickle.close()


def create_model():
	try:
		anime_user_mat_sparse = pickle.load(open(os.path.join(CACHE_FOLDER, DATA_PICKLE), 'rb'))
		mapper = pickle.load(open(os.path.join(CACHE_FOLDER, MAPPER_PICKLE), 'rb'))
	except Exception:
		df_anime = pd.read_csv(
			os.path.join(DATA_FOLDER, ANIME_FILENAME),
			usecols=['anime_id', 'name'],
			dtype={'anime_id': 'int32', 'name': 'str'})
		df_ratings = pd.read_csv(
			os.path.join(DATA_FOLDER, RATINGS_FILENAME),
			usecols=['user_id', 'anime_id', 'rating'],
			dtype={'user_id': 'int32', 'anime_id': 'int32', 'rating': 'int32'})
		print(df_anime.head())
		print(df_ratings.head())
		df_movie_features = df_ratings.pivot_table(
			index='anime_id',
			columns='user_id',
			values='rating',
			aggfunc='mean'
		).fillna(0)
		print(df_movie_features.head())
		num_users = len(df_ratings.user_id.unique())
		num_items = len(df_ratings.anime_id.unique())
		df_ratings_cnt = pd.DataFrame(df_ratings.groupby('rating').size(), columns=['count'])
		total_cnt = num_users * num_items
		rating_zero_cnt = total_cnt - df_ratings.shape[0]
		print(rating_zero_cnt)

		df_movies_cnt = pd.DataFrame(df_ratings.groupby('anime_id').size(), columns=['count'])
		popular_movies = list(set(df_movies_cnt.query('count >= @popularity_thres').index))
		df_ratings_drop_anime = df_ratings[df_ratings.anime_id.isin(popular_movies)]
		df_users_cnt = pd.DataFrame(df_ratings_drop_anime.groupby('user_id').size(), columns=['count'])
		active_users = list(set(df_users_cnt.query('count >= @ratings_thres').index))
		df_ratings_drop_users = df_ratings_drop_anime[df_ratings_drop_anime.user_id.isin(active_users)]
		anime_user_mat = df_ratings_drop_users.pivot_table(index='anime_id', columns='user_id', values='rating', aggfunc='mean').fillna(0)
		anime_user_mat_sparse = csr_matrix(anime_user_mat.values)
		mapper = {
			i: row for i, row in enumerate(list(df_anime.set_index('anime_id').loc[anime_user_mat.index].iterrows()))
		}
		_save_pickle(data=anime_user_mat_sparse, mapper=mapper)

	model_knn = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=20, n_jobs=-1)
	model_knn.fit(anime_user_mat_sparse)
	return model_knn, anime_user_mat_sparse, mapper
