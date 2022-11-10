function updateSelection(css_class) {
    document.querySelectorAll("." + css_class).forEach(a => {
        a.classList.toggle("selected")
    });
}

function createReportButtons(){
    document.querySelectorAll("table.selectable").forEach(table => {
        let head_row = table.querySelector("thead>tr");
        let cell = document.createElement("th");
        cell.textContent = "report as a bot";
        head_row.appendChild(cell);

        let tbody = table.querySelector("tbody");
        tbody.querySelectorAll("tr").forEach(row => {
            let button = document.createElement("button");
            button.type = "button";
            button.textContent = "report";

            let ip_addr = row.children[1].textContent;
            button.onclick = () => {submitForm(ip_addr);};
            
            let cell = row.insertCell(-1);
            cell.appendChild(button);

        });
    }); 
}

function submitForm(ip_addr) {
    let form = document.querySelector("#report_bot_form");
    form.querySelector("input").value = ip_addr;
    form.submit();
}

function createForm(){
    let form = document.createElement("form");
    form.id = "report_bot_form";
    form.method = "get";
    form.action = "/projekty/logs/script.cgi";
    form.style.display = "none";

    let inp = document.createElement("input");
    inp.name = "ip_address";
    inp.value = "";

    form.appendChild(inp);
    document.body.appendChild(form);
}

window.onload = () => {
    createForm();
    createReportButtons();
}
