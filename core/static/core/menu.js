(function () {
    var menus = document.querySelectorAll(".mega-menu-details");

    document.addEventListener("click", function (event) {
        menus.forEach(function (menu) {
            if (!menu.contains(event.target)) {
                menu.removeAttribute("open");
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            menus.forEach(function (menu) {
                menu.removeAttribute("open");
            });
        }
    });
})();
