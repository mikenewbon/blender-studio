function navDrawerSwitch(){
	document.querySelector('body').classList.toggle('nav-drawer-open');
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.navdrawertoggle, .drawer-overlay').forEach((i) => {
        i.addEventListener('click', () => {
			navDrawerSwitch();
        });
    });
});

