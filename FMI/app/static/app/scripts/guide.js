// script.js

'use strict';

// JQuery

var g_guide;
var g_db;
var g_options;


function gallery_select(field, option, selsize) {
    var select_elm = document.getElementsByName(field)[0];
    for (var i = 0; i < select_elm.options.length; i++) {
        if (select_elm.options[i].value === option) {
            select_elm.options[i].selected = !select_elm.options[i].selected;
        }
    }
}

function draw_gallery(field, selsize, gallery) {
    var gallery_div = document.getElementById("gallery_div");
    gallery_div.innerHTML = "";

    var table = document.createElement("table");
    gallery_div.appendChild(table)
    for (var img_ix = 0; img_ix < gallery.length; img_ix++) {
        var key_image = gallery[img_ix];
        var tr = document.createElement("tr");
        table.appendChild(tr)
        var td = document.createElement("td");
        tr.appendChild(td)
        var img_elm = document.createElement("img")
        img_elm.setAttribute("width", "250px");
        img_elm.setAttribute("height", "250px");
        img_elm.setAttribute("src", key_image[1]);
        img_elm.setAttribute("onclick", "gallery_select('"+field+"', '"+key_image[0]+"', '"+selsize+"')");
        td.appendChild(img_elm)
        var td = document.createElement("td");
        tr.appendChild(td)
        var txt = document.createTextNode(key_image[0]);
        td.appendChild(txt)
    }
}

function route_step(route_name, step_name) {
    var input = document.getElementsByName("step_name")[0];
    input.value = step_name;
    var step = g_guide['steps'][step_name];

    if (step['type'] == 'selection') {
        if (step['selection'][0] == 'graph') {
            var storyboard_name = step['selection'][1];
            draw_storyboard(g_guide['storyboard'][storyboard_name], g_db);
        }
    }
    if (step['type'] == 'selection') {
        if (step['selection'][0] == 'gallery') {
            var gallery = step['selection'][1];
            var field = step['facet'];
            var selsize = step['selsize'];
            draw_gallery(field, selsize, gallery);
        }
    }
    if (step['type'] == 'decision') {
        if (step['selection'][0] == 'gallery') {
            var gallery = step['selection'][1];
            var field = step_name
            var selsize = step['selsize'];
            draw_gallery(field, selsize, gallery);
        }
    }
    if (step['type'] == 'destination') {
        window.location.href = step['url'] + "?acountry.keyword=0&agender.keyword=0&aage.keyword=0";
    }
}

function route_definition(route_name) {
    var table = document.getElementById("route_definition_table");
    var steps = g_guide['steps'];
    var route_steps = g_guide['routes'][route_name]['1'];

    for (var step_ix = 0; step_ix < route_steps.length; step_ix++) {
        var step_name = route_steps[step_ix];
        var thead = document.createElement("thead");
        table.appendChild(thead)
        var td = document.createElement("td");
        td.colSpan = "2";
        thead.appendChild(td);
        var bold = document.createElement("b");
        bold.innerHTML = step_name;
        td.appendChild(bold);
        var tbody = document.createElement("tbody");
        table.appendChild(tbody)
        var step = steps[step_name];
        for (var item in step) {
            var tr = document.createElement("tr");
            tbody.appendChild(tr);
            var td = document.createElement("td");
            tr.appendChild(td);
            var txt = document.createTextNode(item);
            td.appendChild(txt);
            var td = document.createElement("td");
            tr.appendChild(td);
            if (step[item] instanceof Array) {
                var txt = step[item][0];
            } else {
                var txt = step[item];
            }
            var txt = document.createTextNode(txt);
            td.appendChild(txt);
        }
        if (step['type'] == 'decision') {
            var dec_table = document.getElementById("decision_table");
            var tr = document.createElement("tr");
            dec_table.appendChild(tr);
            var td = document.createElement("td");
            tr.appendChild(td);
            var label = document.createElement("label");
            td.appendChild(label);
            label.setAttribute("for", step_name);
            label.innerHTML = step_name;
            var select = document.createElement("select");
            td.appendChild(select);
            select.setAttribute("name", step_name);
            select.setAttribute("id", step_name);
            select.setAttribute("class", "form-control");
            select.setAttribute("multiple", true);
            for (var decision in step['decisionstep']) {
                var option = document.createElement("option");
                select.appendChild(option);
                option.setAttribute("value", decision);
                option.text = decision;
            }
        }
    }
}

function route_onchange() {
    var route_name = document.getElementById("route_select").value;
    var table = document.getElementById("route_definition_table");
    table.innerHTML = "";
    document.getElementById("guide_form").submit();

    //var facet = document.getElementById("db_facet_select").value;
    //var params = {
    //    "db_facet_selecion": facet
    //};
    // get the form fields and add them as parameters to the GET. The submit will fire off its own GET request
    // document.getElementById("seeker_form").submit();
    // $.get("/search_survey", params, function (data, status) {
    //    var i = 2;
    // });
}


function guide_route(route_name, step_name, guide, charts) {
    g_guide = guide;
    g_db = charts;

    var select = document.getElementById("route_select");
    select.setAttribute("onChange", "route_onchange()");
    // remove any existing options
    var option = document.createElement("option");
    option.setAttribute("value", "");
    option.text = "Select a route";
    if (route_name == "") {
        option.setAttribute('selected', true);
    }
    select.appendChild(option);
    var routes = guide['routes'];
    for (var route_key in routes) {
        var option = document.createElement("option");
        option.setAttribute("value", route_key);
        option.text = route_key;
        if (route_name == route_key) {
            option.setAttribute('selected', true);
        }
        select.appendChild(option);
    }

    if (route_name != "") {
        route_definition(route_name);
        route_step(route_name, step_name);
    }
}
