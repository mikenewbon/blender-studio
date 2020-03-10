/* global $:false */

(function navigation() {
	function navDrawerToggle() {
		document.querySelector('body').classList.toggle('nav-drawer-open');
	}

	function setCookie(){
		if (document.querySelector('body').classList.contains('nav-drawer-open')){
			Cookies.set('navDrawerOpen', true)
		} else{
			Cookies.set('navDrawerOpen', false)
		}
	}

	function checkNavOpen(){
		if (Cookies.get('navDrawerOpen') == "true"){
			document.querySelector('body').classList.add('nav-drawer-open');
		} else{
			document.querySelector('body').classList.remove('nav-drawer-open');
		}
	}

	document.addEventListener('DOMContentLoaded', () => {
		checkNavOpen();
		document.querySelectorAll('.navdrawertoggle').forEach(i => {
			i.addEventListener('click', () => {
				navDrawerToggle();
				setCookie();
			});
		});
	});

	// TODO(sem): Why do we wrap this function in `$`? What does that do?
	$(() => {
		$('[data-toggle="tooltip"]').tooltip();
	});
})();
