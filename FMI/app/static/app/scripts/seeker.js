// script.js

'use strict';

// JQuery


var g_tiles;
var g_tiles_select;
var g_db;
var g_options;
var g_storyboard;
var g_storyboard_ix;
var g_stats_df;


function getParameterByName(name, url) {
    if (!url) {
        url = window.location.href;
    }
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}

function tab_active() {
    var input = document.getElementsByName("tab")[0];
    var query = window.location.search;
    var tab = getParameterByName("tab");
    input.value = tab;
    var selector = '#tabs a[href=' + tab + ']';
    //$('#tabs a[href="#summary_tab"]').tab('show');
    $(selector).tab('show');
}


function get_workbook() {
    var input = document.getElementsByName("workbook")[0];
    var query = window.location.search;
    var workbook_name = getParameterByName("workbook");
    input.value = workbook_name;
}

function db_facet_select_onchange() {
    var facet = document.getElementById("db_facet_select").value;
    var params = {
        "db_facet_selecion" : facet
    };
    // get the form fields and add them as parameters to the GET. The submit will fire off its own GET request
    // document.getElementById("seeker_form").submit();
    // $.get("/search_survey", params, function (data, status) {
    //    var i = 2;
    // });

    if (facet == "All") {
        draw_storyboard(g_storyboard[g_storyboard_ix], g_db)
        return;
    }
    for (var grid_name in g_storyboard[g_storyboard_ix].layout) {
        var layout = g_storyboard[g_storyboard_ix].layout[grid_name];
        for (var rownr = 0; rownr < layout.length; rownr++) {
            var row = layout[rownr];
            for (var chartnr = 0; chartnr < row.length; chartnr++) {
                var chart_name = layout[rownr][chartnr];
                if (!g_db.hasOwnProperty(chart_name)) continue;
                var db_chart = g_db[chart_name];
                if (db_chart.data.length == 0) continue;
                //var data = new Array(["x_field", "y_field", "metric"]);
                var categories = db_chart.data[0]
                var data = new Array(categories);
                var datarownr = 1;
                for (var ti in g_tiles) {
                    var tile_coor = g_tiles[ti];
                    if (facet == tile_coor.facet_tile && chart_name == tile_coor.chart_name) {
                        var x_found = false;
                        var y_found = false;
                        for (var xi = 0; xi < data.length; xi++) {
                            if (data[xi][0] == tile_coor.x_field) {
                                x_found = true;
                                break;
                            }
                        }
                        if (!x_found) {
                            data[datarownr] = new Array(categories.length).fill(0);
                            xi = datarownr;
                            datarownr++;
                        }
                        data[xi][0] = tile_coor.x_field;
                        for (var yi = 0; yi < categories.length; yi++) {
                            if (categories[yi] == tile_coor.y_field) {
                                data[xi][yi] = tile_coor.metric;
                                y_found = true;
                                break;
                            }
                        }
                    }
                }
                // add dummy row
                if (datarownr == 1) {
                    data[datarownr] = new Array(categories.length).fill(0);
                    data[datarownr][0] = "";
                }
                var dt = google.visualization.arrayToDataTable(data, false);
                // only redraw for the active storyboard
                if (g_db[chart_name].google_db != 'undefined') {
                    g_db[chart_name].google_db.draw(dt, g_options);
                }
            }
        }
    }
}


function facet_dashboard(tiles_select, tiles) {

    g_tiles = tiles;
    g_tiles_select = tiles_select;

    var selectList = document.getElementById("db_facet_select");
    selectList.setAttribute("onChange", "db_facet_select_onchange()");

    var option = document.createElement("option");
    option.setAttribute("value", "All");
    option.text = "All";
    selectList.appendChild(option);
    for (var facet_tile in tiles_select) {
        var optgroup = document.createElement("optgroup");
        optgroup.setAttribute("label", facet_tile);
        optgroup.text = facet_tile;
        selectList.appendChild(optgroup);
        for (var fi = 0; fi < tiles_select[facet_tile].length; fi++) {
            var facet_value = tiles_select[facet_tile][fi];
            var option = document.createElement("option");
            option.setAttribute("value", facet_value);
            option.text = facet_value;
            selectList.appendChild(option);
        }
    }
}


function add_table_row(tbody, cells) {
    var tr = document.createElement("tr");
    tbody.appendChild(tr)
    for (var ix = 0; ix < cells.length; ix++) {
        var cell = cells[ix];
        var td = document.createElement("td");
        tr.appendChild(td)
        var txt = document.createTextNode(cell);
        td.appendChild(txt)
    }
}



function dashboard_definition(storyboard_ix) {
    g_storyboard_ix = storyboard_ix;
    var table = document.getElementById("db_layout_table");

    for (var grid_name in g_storyboard[storyboard_ix].layout) {
        var thead = document.createElement("thead");
        table.appendChild(thead)
        var td = document.createElement("td");
        td.colSpan = "2";
        thead.appendChild(td)
        var txt = document.createTextNode(grid_name);
        td.appendChild(txt)
        var tbody = document.createElement("tbody");
        table.appendChild(tbody)
        var layout = g_storyboard[storyboard_ix].layout[grid_name];
        for (var rownr = 0; rownr < layout.length; rownr++) {
            var row = layout[rownr];
            var tr = document.createElement("tr");
            tbody.appendChild(tr)
            for (var chartnr = 0; chartnr < row.length; chartnr++) {
                var chart_name = layout[rownr][chartnr];
                //$("#db_layout_div").append($('<tr>')).append($('<td Grid>'));
                var td = document.createElement("td");
                tr.appendChild(td)
                var txt = document.createTextNode(chart_name);
                td.appendChild(txt)
            }
        }
    }
}

function db_storyboard_onchange() {
    var storyboard_ix = document.getElementById("db_storyboard_select").value;
    // $("#db_layout_div").append($('<table>')).append($('<tr>')).append($('<td Grid>'));
    var table = document.getElementById("db_layout_table");
    //var nrrow = table.rows.length;
    //for (var rownr = 0; rownr<nrrow; rownr++) {
    //   table.deleteRow(0);
    //}
    var tb = table.querySelectorAll('tbody');
    for (var i = 0; i < tb.length; i++) {
        tb[i].parentNode.removeChild(tb[i]);
    }
    var th = table.querySelectorAll('thead');
    for (var i = 0; i < th.length; i++) {
        th[i].parentNode.removeChild(th[i]);
    }
    dashboard_definition(storyboard_ix)
    draw_storyboard(g_storyboard[storyboard_ix], g_db)
}


function chart_selecion_onchange() {
    var chart_name = document.getElementById("chart_selecion_select").value;
    var table = document.getElementById("chart_definition_table");
    table.innerHTML = "";
    var thead = document.createElement("thead");
    table.appendChild(thead)
    var td = document.createElement("td");
    td.colSpan = "2";
    thead.appendChild(td)
    var txt = document.createTextNode(chart_name);
    td.appendChild(txt)
    var tbody = document.createElement("tbody");
    table.appendChild(tbody)
    var chart = g_db[chart_name];
    add_table_row(tbody, ['Title', chart.chart_title]);
    add_table_row(tbody, ['Type', chart.chart_type]);
    add_table_row(tbody, ['X', chart.X_facet.field]);
    if ('Y_facet' in chart) {
        add_table_row(tbody, ['Y', chart.Y_facet.field]);
    }
}

function story_dashboard(storyboard, charts) {
    g_storyboard = storyboard;
    g_db = charts;

    var select = document.getElementById("db_storyboard_select");
    select.setAttribute("onChange", "db_storyboard_onchange()");
    // remove any existing options
    select.options.length = 0;
    var active_nr;
    for (var ix=0; ix<storyboard.length; ix++) {
        var option = document.createElement("option");
        option.setAttribute("value", ix);
        option.text = storyboard[ix].name;
        if (storyboard[ix].active == true) {
            option.setAttribute('selected', true);
            active_nr = ix;
        }
        select.appendChild(option);
    }
    var chart_selection_div = document.getElementById("chart_selection_div");
    var select = document.createElement("select");
    select.setAttribute("id", "chart_selecion_select");
    select.setAttribute("onChange", "chart_selecion_onchange()");
    chart_selection_div.appendChild(select);
    // remove any existing options
    select.options.length = 0;
    var active_nr;
    for (var chart_name in charts) {
        var option = document.createElement("option");
        option.setAttribute("value", chart_name);
        option.text = chart_name;
        select.appendChild(option);
    }
    //chart_definitions(charts);
    dashboard_definition(active_nr);
    draw_storyboard(g_storyboard[active_nr], g_db)
}

function add_table_row_cells(table, cells) {
    var tr = document.createElement("tr");
    table.appendChild(tr)
    for (var cell in cells) {
        var td = document.createElement("td");
        tr.appendChild(td)
        var txt = document.createTextNode(cells[cell]);
        td.appendChild(txt)
    }
}

function correlation_selecion_onchange() {
    var question = document.getElementById("correlation_selecion_select").value;
}

function question_selecion_onchange() {
    var question = document.getElementById("question_selecion_select").value;
    var table = document.getElementById("stats_table");
    var tbody = table.getElementsByTagName("tbody")[0]
    tbody.innerHTML = "";
    if (question == "Select") {
        return;
    }
    for (var stat in g_stats_df) {
        if (question == g_stats_df[stat].question) {
            var mean = g_stats_df[stat].mean.toFixed(2);
            var std = g_stats_df[stat].std.toFixed(2);
            add_table_row_cells(tbody, [g_stats_df[stat].answer, g_stats_df[stat].value, g_stats_df[stat].count,
                                       mean, std, g_stats_df[stat].min, g_stats_df[stat].max]);
        }
    }
    var $table = $("#stats_table").tablesorter({
        widgets: ["zebra", "filter", "resizable"],
        widgetOptions: {
            // class name applied to filter row and each input
            filter_cssFilter: 'tablesorter-filter',
            // search from beginning
            filter_startsWith: true,
            // Set this option to false to make the searches case sensitive
            filter_ignoreCase: true,
            filter_reset: '.reset',
            resizable_addLastColumn: true
        },
    });
    $(table).trigger("update");
    $(table).trigger("appendCache");
}

function facts_norms(stats_df) {
    g_stats_df = stats_df;

    var question_selection_div = document.getElementById("question_selecion_div");
    if (question_selection_div == null) {
        return;
    }
    var select = document.createElement("select");
    select.setAttribute("id", "question_selecion_select");
    select.setAttribute("onChange", "question_selecion_onchange()");
    question_selection_div.appendChild(select);
    // remove any existing options
    select.options.length = 0;
    var questions = ["Select"];
    for (var stat in stats_df) {
        var question = stats_df[stat].question;
        var found = false;
        for (var qix = 0; qix < questions.length; qix++) {
            if (question == questions[qix]) {
                found = true;
                break;
            }
        }
        if (!found) {
            questions.push(question);
        }
    }
    for (question in questions) {
        var option = document.createElement("option");
        option.setAttribute("value", questions[question]);
        option.text = questions[question];
        select.appendChild(option);
    }
    var correlation_selection_div = document.getElementById("correlation_selecion_div");
    var select = document.createElement("select");
    select.setAttribute("id", "correlation_selecion_select");
    select.setAttribute("onChange", "correlation_selecion_onchange()");
    correlation_selection_div.appendChild(select);
    for (question in questions) {
        var option = document.createElement("option");
        option.setAttribute("value", questions[question]);
        option.text = questions[question];
        select.appendChild(option);
    }

    var stats_facets_b = document.getElementById("stats_facets_b");
    var facets = "";
    for (var facet_tile in g_tiles_select) {
        if (facets == "") {
            facets = facet_tile;
        } else {
            facets = facets.concat(", ", facet_tile);
        }
    }
    var txt = document.createTextNode(facets);
    stats_facets_b.appendChild(txt);
}

//$("option[value*='^']").click(function () {
//    $(this).toggleClass('red');
//    var option = $(this)[0];
//    option.text = "Contemporaty/1 (101/85)"
//    option.value = "Contempory^0"
//});

$("#_reset").click(function () {
    var input = document.getElementsByName("tab")[0];
    var ul = document.getElementById("tabs");
    var items = ul.getElementsByTagName("li");
    for (var i = 0; i < items.length; ++i) {
        var li = items[i];
        var c = li.className;
        if (c == "active") {
            var anchor = li.getElementsByTagName('a')[0];
            var href = anchor.href;
            var n = href.lastIndexOf("#");
            var tab = href.substr(n, href.length - 1);
            input.value = tab;
            document.getElementById("_reset").href = "?q=&tab="+encodeURIComponent(tab);
        }
    }
});


// load the hidden input "tab" with the current active tabpage
$("#_filter").click(function () {
    var input = document.getElementsByName("tab")[0];
    var ul = document.getElementById("tabs");
    var items = ul.getElementsByTagName("li");
    for (var i = 0; i < items.length; ++i) {
        var li = items[i];
        var c = li.className;
        if (c == "active") {
            var anchor = li.getElementsByTagName('a')[0];
            var href = anchor.href;
            var n = href.lastIndexOf("#");
            var tab = href.substr(n, href.length - 1);
            input.value = tab;
        }
    }
});


// submit the form when a botton is pressed for Keyword load or search
function keyword_button_submit(button) {
    var input = document.getElementsByName("keyword_button")[0];
    input.value = button;
    input.form.submit()
}


// the selected keywords are copied to the Search field. This is replaced by the Search button in the keyword input text field.
$("#_keywords_filter").click(function () {
    var search = ""
    var facet_keyword = document.getElementsByName("facet_keyword")[0];
    var options = facet_keyword.options;
    for (var i = 0; i < options.length; ++i) {
        var option = options[i];
        var selected = option.selected;
        if (selected == true) {
            option.selected = false;
            var key = option.value;
            if (search == "") {search = key} else {search = search + " OR " + key}
        }
    }
    var q = document.getElementsByName("q")[0];
    q.value = search
});

$(document).ready(function () {

    $('[data-toggle="tooltip"]').tooltip(); 

    var $table = $("#stats_table").tablesorter({
        widgets: ["zebra", "filter", "resizable"],
        widgetOptions: {
            // class name applied to filter row and each input
            filter_cssFilter: 'tablesorter-filter',
            // search from beginning
            filter_startsWith: true,
            // Set this option to false to make the searches case sensitive
            filter_ignoreCase: true,
            filter_reset: '.reset',
            resizable_addLastColumn: true
        },
    });


    var $table = $("#corr_table").tablesorter({
        widgets: ["zebra", "filter", "resizable"],
        widgetOptions: {
            // class name applied to filter row and each input
            filter_cssFilter: 'tablesorter-filter',
            // search from beginning
            filter_startsWith: true,
            // Set this option to false to make the searches case sensitive
            filter_ignoreCase: true,
            filter_reset: '.reset',
            resizable_addLastColumn: true
        },
    });
 
});


tab_active();
get_workbook();




