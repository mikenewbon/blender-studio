function navDrawerSwitch(){

    document.querySelectorAll('.nav-drawer').forEach((i) => {
        i.classList.toggle('open');
    });
	document.querySelector('.navbar').classList.toggle('nav-drawer-offset-open');
	document.querySelector('.navbar-secondary').classList.toggle('nav-drawer-offset-open');
	document.querySelector('.content-holder').classList.toggle('nav-drawer-offset-open');
	document.querySelector('.screen-overlay').classList.toggle('nav-drawer-open');
	document.querySelector('footer').classList.toggle('nav-drawer-offset-open');
    if(document.querySelector('.nav-drawer').classList.contains('open')){
        document.querySelectorAll('.navdrawertoggle i').forEach((i) => {
			i.innerText = 'close';
		})
    } else{
        document.querySelectorAll('.navdrawertoggle i').forEach((i) => {
			i.innerText = 'menu';
		})
    }
}

document.addEventListener("DOMContentLoaded", function () {
	console.log('hello')
    document.querySelectorAll('.navdrawertoggle').forEach((i) => {
        i.addEventListener('click', () => {
            navDrawerSwitch();
        });
    });

});

