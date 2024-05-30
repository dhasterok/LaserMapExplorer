// fixes issues with js and fontawsome loading issues
document.addEventListener("DOMContentLoaded", function() {
    var links = document.querySelectorAll('link[rel="preload"]');
    links.forEach(function(link) {
        if (link.href.includes('fa-brands-400.woff2')) {
            link.setAttribute('crossorigin', 'anonymous');
        }
        if (link.href.includes('fa-solid-900.woff2')) {
            link.setAttribute('crossorigin', 'anonymous');
        }
        if (link.href.includes('fa-regular-400.woff2')) {
            link.setAttribute('crossorigin', 'anonymous');
        }
    });
});
