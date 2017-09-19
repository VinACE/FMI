﻿// script.js

'use strict';

// JQuery
var g_db;
var g_facet_data;
var g_tiles_d;
var g_tiles_select;
var g_options;
var g_storyboard;
var g_storyboard_ix;
var g_storyboard_tab_activated;
var g_stats_df;

function benchmark_select_onchange() {
    var facet_value = document.getElementById("benchmark_select").value;
    var input = document.getElementsByName("benchmark")[0];
    input.value = facet_value;
    var form_elm = document.getElementById("guide_form");
    if (form_elm == null) {
        var form_elm = document.getElementById("seeker_form");
    }
    form_elm.submit();
}

function tile_facet_select_onchange() {
    var facet_field = document.getElementById("tile_facet_select").value;
    var input = document.getElementsByName("tile_facet_field")[0];
    input.value = facet_field;
    var form_elm = document.getElementById("guide_form");
    if (form_elm == null) {
        var form_elm = document.getElementById("seeker_form");
    }
    form_elm.submit();
}

function tile_value_select_onchange() {
    var facet_value = document.getElementById("tile_value_select").value;
    var params = {
        "db_facet_selecion": facet_value
    };
    // get the form fields and add them as parameters to the GET. The submit will fire off its own GET request
    // document.getElementById("seeker_form").submit();
    // $.get("/search_survey", params, function (data, status) {
    //    var i = 2;
    // });

    //if (facet_value == "All") {
    //    draw_dashboard(g_storyboard[g_storyboard_ix], g_db, "All", "dashboard_div")
    //    return;
    //}
    for (var grid_name in g_storyboard[g_storyboard_ix].layout) {
        var layout = g_storyboard[g_storyboard_ix].layout[grid_name];
        for (var rownr = 0; rownr < layout.length; rownr++) {
            var row = layout[rownr];
            for (var chartnr = 0; chartnr < row.length; chartnr++) {
                var chart_name = layout[rownr][chartnr];
                var chart = g_db[chart_name]
                if (!g_db.hasOwnProperty(chart_name)) continue;
                var chart = g_db[chart_name];
                var X_facet = chart['X_facet']
                var div_card_header = document.getElementById(chart_name + "_title");
                div_card_header.innerHTML = "<b>" + chart['chart_title'] + "</b>";
                if (g_tiles_d[chart_name][facet_value] != null) {
                    var chart_data = g_tiles_d[chart_name][facet_value]['chart_data'];
                    if (facet_value != 'All') {
                        div_card_header.innerHTML = div_card_header.innerHTML +
                            " / <font color='red'>" + facet_value + "</font>";
                    }
                } else {
                    var chart_data = g_tiles_d[chart_name]['All']['chart_data'];
                }
                if ("type" in X_facet) {
                    if (X_facet['type'] == 'date') {
                        for (var rix = 1; rix < chart_data.length; rix++) {
                            var s = chart_data[rix][0];
                            if (typeof s === 'string') {
                                var d = new Date(s);
                                chart_data[rix][0] = d
                            }
                        }
                    }
                }
                if (chart_data.length == 0) continue;
                if (chart['chart_type'] == 'RadarChart') {
                    d3_chart(chart_name, chart, facet_value, [1, 2, 3]);
                } else {
                    var dt = google.visualization.arrayToDataTable(chart_data, false);
                    var view = new google.visualization.DataView(dt);
                    g_db[chart_name].datatable = dt;
                    g_db[chart_name].view = view;
                    // only redraw for the active storyboard
                    if (typeof g_db[chart_name].google_db != 'undefined') {
                        g_db[chart_name].google_db.draw(dt, g_options);
                    }
                }
            }
        }
    }
}


function fill_tiles(facets_data, tiles_select, tiles_d) {
    g_facet_data = facet_data
    g_tiles_select = tiles_select;
    g_tiles_d = tiles_d;

    var selectList = document.getElementById("benchmark_select");
    selectList.setAttribute("onChange", "benchmark_select_onchange()");
    var option = document.createElement("option");
    option.setAttribute("value", "All");
    option.text = "All";
    selectList.appendChild(option);
    for (var facet_field in facets_data) {
        var facet_data = facets_data[facet_field];
        var optgroup = document.createElement("optgroup");
        optgroup.setAttribute('value', facet_field);
        optgroup.setAttribute("label", facet_data['label']);
        selectList.appendChild(optgroup);
        var values = facet_data['values']
        for (var vi = 0; vi < values.length; vi++) {
            var facet_value = values[vi];
            var option = document.createElement("option");
            option.setAttribute("value", facet_value);
            if (facet_data['benchmark'] == facet_value) {
                option.setAttribute('selected', true);
            }
            option.text = facet_value;
            optgroup.appendChild(option);
        }
    }

    var selectList = document.getElementById("tile_facet_select");
    selectList.setAttribute("onChange", "tile_facet_select_onchange()");
    var option = document.createElement("option");
    option.setAttribute("value", "All");
    option.text = "All";
    selectList.appendChild(option);
    for (var facet_field in facets_data) {
        var facet_data = facets_data[facet_field];
        var option = document.createElement("option");
        option.setAttribute('value', facet_field);
        if (facet_data['selected'] == true) {
            option.setAttribute('selected', true);
        }
        option.text = facet_data['label'];
        selectList.appendChild(option);
    }

    var selectList = document.getElementById("tile_value_select");
    selectList.setAttribute("onChange", "tile_value_select_onchange()");
    // "All" provided by tiles_select
    //var option = document.createElement("option");
    //option.setAttribute("value", "All");
    //option.text = "All";
    //selectList.appendChild(option);
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

function draw_dashboard(dashboard, charts, facet_value, container_elm) {
    //var dashboard_div = document.getElementById("dashboard_div");
    var dashboard_div = document.getElementById(container_elm);
    dashboard_div.innerHTML = "";
    for (var chart_name in charts) {
        var db_chart = charts[chart_name];
        delete db_chart.google_db;
    }

    for (var grid_name in dashboard.layout) {
        var layout = dashboard.layout[grid_name];
        for (var rownr = 0; rownr < layout.length; rownr++) {
            var row = layout[rownr];

            var div_row = document.createElement("div");
            div_row.setAttribute("class", "row iff-margin-t15");
            dashboard_div.appendChild(div_row);

            var l_width = 12 / row.length;
            for (var chartnr = 0; chartnr < row.length; chartnr++) {
                var chart_name = layout[rownr][chartnr];
                var chart = charts[chart_name];
                var div_col = document.createElement("div");
                div_col.setAttribute("class", "col-md-" + l_width);
                div_row.appendChild(div_col);
                var div_card = document.createElement("div");
                div_card.setAttribute("class", "iff-card-6");
                div_col.appendChild(div_card);

                var div_card_header = document.createElement("div");
                div_card_header.setAttribute("class", "iff-card-header");
                div_card_header.setAttribute("id", chart_name + "_title");
                div_card.appendChild(div_card_header);
                div_card_header.innerHTML = "<b>" + chart['chart_title'] + "</b>";
                var div_card_body = document.createElement("div");
                div_card_body.setAttribute("class", "iff-card-body");
                div_card.appendChild(div_card_body);

                var div_db = document.createElement("div");
                div_db.setAttribute("id", chart_name + "_dbdiv");
                //div_db.setAttribute("style", "width: 100%; height: 100%");
                div_db.setAttribute("style", "width: 100%;");
                div_card_body.appendChild(div_db);
                var div_cont_db = document.createElement("div");
                div_cont_db.setAttribute("class", "container-fluid");
                div_db.appendChild(div_cont_db);
                if ('help' in chart) {
                    //var help_txt = document.createTextNode(chart['help']);
                    var div_row_db = document.createElement("div");
                    div_row_db.setAttribute("class", "row");
                    div_cont_db.appendChild(div_row_db);
                    var div_col_db = document.createElement("div");
                    div_col_db.setAttribute("class", "col-md-12");
                    div_row_db.appendChild(div_col_db);
                    var help_txt = document.createElement("b");
                    help_txt.innerHTML = chart['help'];
                    div_col_db.appendChild(help_txt);
                }
                var nrcontrols = 1
                if ('controls' in chart) {
                    nrcontrols = chart['controls'].length;
                }
                var div_row_db = document.createElement("div");
                div_row_db.setAttribute("class", "row");
                div_cont_db.appendChild(div_row_db);
                var c_width = 12 / nrcontrols;
                for (var controlnr = 0; controlnr < nrcontrols; controlnr++) {
                    var div_col_db = document.createElement("div");
                    div_col_db.setAttribute("class", "col-md-" + c_width);
                    div_row_db.appendChild(div_col_db);
                    var div_ct = document.createElement("div");
                    div_ct.setAttribute("id", chart_name + "_ct" + (controlnr + 1) + "div");
                    div_col_db.appendChild(div_ct);
                }
                var div_row_db = document.createElement("div");
                div_row_db.setAttribute("class", "row");
                div_cont_db.appendChild(div_row_db);
                var div_col_db = document.createElement("div");
                div_col_db.setAttribute("class", "col-md-12");
                div_row_db.appendChild(div_col_db);
                var div_ch = document.createElement("div");
                div_ch.setAttribute("id", chart_name + "_chdiv");
                div_col_db.appendChild(div_ch);
            }
        }
    }

    for (var grid_name in dashboard.layout) {
        var layout = dashboard.layout[grid_name];
        for (var rownr = 0; rownr < layout.length; rownr++) {
            var row = layout[rownr];
            for (var chartnr = 0; chartnr < row.length; chartnr++) {
                var chart_name = layout[rownr][chartnr];
                if (!charts.hasOwnProperty(chart_name)) continue;
                var chart = charts[chart_name];
                var div_card_header = document.getElementById(chart_name + "_title");
                if (g_tiles_d[chart_name][facet_value] != null) {
                    var chart_data = g_tiles_d[chart_name][facet_value]['chart_data'];
                    if (facet_value != 'All') {
                        div_card_header.innerHTML = div_card_header.innerHTML +
                            " / <font color='red'>" + facet_value + "</font>";
                    }
                } else {
                    var chart_data = g_tiles_d[chart_name]['All']['chart_data'];
                }
                if (chart_data.length == 0) continue;
                if (chart['chart_type'] == 'RadarChart') {
                    d3_chart(chart_name, chart, facet_value, [1, 2, 3]);
                } else {
                    google_chart(chart_name, chart, facet_value);
                }
            }
        }
    }
}


function dashboard_definition(storyboard_ix) {
    g_storyboard_ix = storyboard_ix;
    var table = document.getElementById("db_layout_table");
    if (table != null) {
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
}

function storyboard_onchange() {
    var storyboard_ix = document.getElementById("storyboard_select").value;
    var input = document.getElementsByName("dashboard_name")[0];
    var dashboard_name = g_storyboard[storyboard_ix]['name'];
    input.value = dashboard_name;
    var facet_value = document.getElementById("tile_value_select").value;

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
    draw_dashboard(g_storyboard[storyboard_ix], g_db, facet_value, "dashboard_div")
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

function draw_storyboard(storyboard, dashboard_name, charts) {
    g_storyboard = storyboard;
    g_db = charts;

    var select = document.getElementById("storyboard_select");
    if (select != null) {
        select.setAttribute("onChange", "storyboard_onchange()");
        // remove any existing options
        select.options.length = 0;
        var active_nr;
        for (var ix = 0; ix < storyboard.length; ix++) {
            var option = document.createElement("option");
            option.setAttribute("value", ix);
            option.text = storyboard[ix].name;
            if (storyboard[ix].active == true || storyboard[ix].name == dashboard_name) {
                option.setAttribute('selected', true);
                active_nr = ix;
            }
            select.appendChild(option);
        }
    }
    var chart_selection_div = document.getElementById("chart_selection_div");
    if (chart_selection_div != null) {
        var select = document.createElement("select");
        select.setAttribute("id", "chart_selecion_select");
        select.setAttribute("onChange", "chart_selecion_onchange()");
        chart_selection_div.appendChild(select);
        // remove any existing options
        select.options.length = 0;
        for (var chart_name in charts) {
            var option = document.createElement("option");
            option.setAttribute("value", chart_name);
            option.text = chart_name;
            select.appendChild(option);
        }
    }
    //chart_definitions(charts);
    dashboard_definition(active_nr);
    draw_dashboard(g_storyboard[active_nr], g_db, "All", "dashboard_div")
}

