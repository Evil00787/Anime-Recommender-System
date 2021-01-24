from flask import Flask, jsonify
import recommender as rec
from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/recommend/<string:name>', methods=['GET'])
@cross_origin()
def get_recommendation(name):
	name_formatted = name.replace("_", " ")
	data = rec.make_recommendation(
		model_knn=model_knn,
		data=movie_user_mat_sparse,
		fav_anime=name_formatted,
		mapper=anime_to_idx,
		links=links
	)
	if not data:
		return jsonify({"error": "Not found"}), 204
	return jsonify(data), 200


if __name__ == '__main__':
	model_knn, movie_user_mat_sparse, anime_to_idx = rec.create_model()
	links = rec.get_id_to_link_map(anime_to_idx.values())
	app.run(debug=True)
