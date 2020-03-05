function navDrawerToggle(){
	document.querySelector("body").classList.toggle("nav-drawer-open");
}

document.addEventListener("DOMContentLoaded", function () {

	document.querySelectorAll(".navdrawertoggle").forEach((i) => {
		i.addEventListener("click", () =>{
			navDrawerToggle();
		})
	})

});

$(function () {
	$('[data-toggle="tooltip"]').tooltip()
  })