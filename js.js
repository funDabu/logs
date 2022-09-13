function updateSelection(css_class) {
    document.querySelectorAll("." + css_class).forEach(a => {
        a.classList.toggle("selected")
    });
}