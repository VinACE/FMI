// script.js

'use strict';

// JQuery



function draw_storyboard(storyboard, charts) {
    var dashboard_div = document.getElementById("dashboard_div");
    dashboard_div.innerHTML = "";
    for (var chart_name in charts) {
        var db_chart = charts[chart_name];
        delete db_chart.google_db;
    }

    for (var grid_name in storyboard.layout) {
        var layout = storyboard.layout[grid_name];
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
                div_card.appendChild(div_card_header);
                var title_txt = document.createElement("b");
                title_txt.innerHTML = chart['chart_title'];
                div_card_header.appendChild(title_txt);
                var div_card_body = document.createElement("div");
                div_card_body.setAttribute("class", "iff-card-body");
                div_card.appendChild(div_card_body);

                var div_db = document.createElement("div");
                div_db.setAttribute("id", chart_name + "_dbdiv");
                div_db.setAttribute("style", "width: 100%; height: 100%");
                div_card_body.appendChild(div_db);
                var div_cont_db = document.createElement("div");
                div_cont_db.setAttribute("class", "container");
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

    for (var grid_name in storyboard.layout) {
        var layout = storyboard.layout[grid_name];
        for (var rownr = 0; rownr < layout.length; rownr++) {
            var row = layout[rownr];
            for (var chartnr = 0; chartnr < row.length; chartnr++) {
                var chart_name = layout[rownr][chartnr];
                if (!charts.hasOwnProperty(chart_name)) continue;
                var chart = charts[chart_name];
                if (chart.data.length == 0) continue;
                if (chart['chart_type'] == 'RadarChart') {
                    d3_chart(chart_name, chart, [1, 2, 3]);
                } else {
                    google_chart(chart_name, chart);
                }
            }
        }
    }
}







