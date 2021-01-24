$(document).ready(function(){
    $('.owl-carousel').owlCarousel({
        loop:true,
        margin:10,
        lazyLoad: true,
        responsiveClass:true,
        responsive:{
            0:{
                items:2,
                nav:false
            },
            600:{
                items:5,
                nav:true
            },
            1000:{
                items:7,
                nav:true,
            }
        }
    })
    var form = document.getElementById("myForm");
    form.addEventListener("submit", function (e) {
            getRecommendations();
    });
});

function getRecommendations() {
    var inputVal = document.getElementById("animeNameInput").value.replace(/ /g,"_");
    if (inputVal != ''){
        openNav();
        httpGetAsync('http://127.0.0.1:5000/recommend/' + inputVal, onRecommendationsLoaded);
    }

}

function httpGetAsync(theUrl, callback) {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() { 
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
            callback(xmlHttp.responseText);
    }
    xmlHttp.open("GET", theUrl, true);
    xmlHttp.send(null);
}


function onRecommendationsLoaded(response) {
    rec_map = JSON.parse(response);
    var carousel = $('.owl-carousel');
    var arr = [];
    for (let key of Object.keys(rec_map)) {
        arr.push({
            id: rec_map[key]["id"],
            name: key,
            img: rec_map[key]["img"],
            dist: rec_map[key]["dist"]
        });
    }
    arr.sort((a, b) => b.dist - a.dist);
    arr.forEach(function (el, i) {
        var html = '<a href="https://www.myanimelist.net/anime/'+ el.id +'"><div class="card"> <img src='+ el.img +' alt='+el.name+' style="width:100%"><div class="container"><h4><b>'+el.name+'</b></h4><p>'+"Similarity: " + el.dist+'%</p></div></div>';
        if(i == 0)
            carousel.trigger('replace.owl.carousel', html);
        else carousel.trigger('add.owl.carousel', [html]);
    });
    carousel.trigger('refresh.owl.carousel');
    closeNav();
    
}


/* Open */
function openNav() {
    document.getElementById("overlay").style.display = "block";
}
  
  /* Close */
  function closeNav() {
    document.getElementById("overlay").style.display = "none";
}

