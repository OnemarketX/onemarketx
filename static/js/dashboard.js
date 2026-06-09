const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebarOverlay");
const openBtn = document.getElementById("openSidebar");
const closeBtn = document.getElementById("closeSidebar");

if(openBtn){
    openBtn.addEventListener("click", () => {
        sidebar.classList.add("active");
        overlay.classList.add("active");
    });
}

if(closeBtn){
    closeBtn.addEventListener("click", () => {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    });
}

if(overlay){
    overlay.addEventListener("click", () => {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    });
}



const notificationToggle =
document.getElementById(
    "notificationToggle"
);

const notificationDropdown =
document.getElementById(
    "notificationDropdown"
);

if(
    notificationToggle &&
    notificationDropdown
){

    notificationToggle.onclick = () => {

        notificationDropdown.classList.toggle(
            "active"
        );

    };

    document.addEventListener(
        "click",
        function(e){

            if(
                !notificationToggle.contains(e.target)
                &&
                !notificationDropdown.contains(e.target)
            ){

                notificationDropdown.classList.remove(
                    "active"
                );

            }

        }
    );

}