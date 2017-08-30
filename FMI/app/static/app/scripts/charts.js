// script.js

'use strict';

// JQuery

function d3_chart(chart_name, chart_def, colIndexes) {
    var chdivid = '#' + chart_name + '_chdiv'
    var ctdivsid = ['#' + chart_name + '_ct1div', '#' + chart_name + '_ct2div']
    var w = 500,
        h = 500;

    var colorscale = d3.scale.category10();

    //Legend titles
    //var LegendOptions = ['Smartphone', 'Tablet'];

    //Data
    //var d = [
    //          [
    //            { axis: "Email", value: 0.59 },
    //            { axis: "Social Networks", value: 0.56 },
    //            { axis: "Internet Banking", value: 0.42 },
    //            { axis: "News Sportsites", value: 0.34 },
    //            { axis: "Search Engine", value: 0.48 },
    //            { axis: "View Shopping sites", value: 0.14 },
    //            { axis: "Paying Online", value: 0.11 },
    //            { axis: "Buy Online", value: 0.05 },
    //            { axis: "Stream Music", value: 0.07 },
    //            { axis: "Online Gaming", value: 0.12 },
    //            { axis: "Navigation", value: 0.27 },
    //            { axis: "App connected to TV program", value: 0.03 },
    //            { axis: "Offline Gaming", value: 0.12 },
    //            { axis: "Photo Video", value: 0.4 },
    //            { axis: "Reading", value: 0.03 },
    //            { axis: "Listen Music", value: 0.22 },
    //            { axis: "Watch TV", value: 0.03 },
    //            { axis: "TV Movies Streaming", value: 0.03 },
    //            { axis: "Listen Radio", value: 0.07 },
    //            { axis: "Sending Money", value: 0.18 },
    //            { axis: "Other", value: 0.07 },
    //            { axis: "Use less Once week", value: 0.08 }
    //          ], [
    //            { axis: "Email", value: 0.48 },
    //            { axis: "Social Networks", value: 0.41 },
    //            { axis: "Internet Banking", value: 0.27 },
    //            { axis: "News Sportsites", value: 0.28 },
    //            { axis: "Search Engine", value: 0.46 },
    //            { axis: "View Shopping sites", value: 0.29 },
    //            { axis: "Paying Online", value: 0.11 },
    //            { axis: "Buy Online", value: 0.14 },
    //            { axis: "Stream Music", value: 0.05 },
    //            { axis: "Online Gaming", value: 0.19 },
    //            { axis: "Navigation", value: 0.14 },
    //            { axis: "App connected to TV program", value: 0.06 },
    //            { axis: "Offline Gaming", value: 0.24 },
    //            { axis: "Photo Video", value: 0.17 },
    //            { axis: "Reading", value: 0.15 },
    //            { axis: "Listen Music", value: 0.12 },
    //            { axis: "Watch TV", value: 0.1 },
    //            { axis: "TV Movies Streaming", value: 0.14 },
    //            { axis: "Listen Radio", value: 0.06 },
    //            { axis: "Sending Money", value: 0.16 },
    //            { axis: "Other", value: 0.07 },
    //            { axis: "Use less Once week", value: 0.17 }
    //          ]
    //];

    //Options for the Radar chart, other than default
    var chart_title = chart_def['chart_title'];
    if ('options' in chart_def) {
        var options = chart_def['options'];
        if ('width' in options) {
            w = options['width'];
        }
        if ('height' in options) {
            h = options['height'];
        }
    }
    var mycfg = {
        w: w,
        h: h,
        maxValue: 0.6,
        levels: 6,
        //ExtraWidthX: 300
    }

    //Call function to draw the Radar chart
    //Will expect that data is in %'s
    var data = [];
    var LegendOptions = [];
    for (var colnr = 1; colnr < chart_def['data'][0].length; colnr++) {
        var series = [];
        for (var rownr = 1; rownr < chart_def['data'].length; rownr++) {
            var axis = chart_def['data'][rownr][0];
            var value = chart_def['data'][rownr][colnr];
            series.push({ 'axis': axis, 'value': value });
        }
        if (colIndexes.indexOf(colnr) >= 0) {
            LegendOptions.push(chart_def['data'][0][colnr]);
            data.push(series);
        }
    }

    RadarChart.draw(chdivid, data, mycfg);

    ////////////////////////////////////////////
    /////////// Initiate legend ////////////////
    ////////////////////////////////////////////

    var svg = d3.select(chdivid)
        .selectAll('svg')

    //Create the title for the legend
    var text = svg.append("text")
        .attr("class", "title")
        .attr("x", 10)
        .attr("y", 20)
        .attr("font-size", "12px")
        .attr("font-weight", "bold")
        .attr("fill", "#404040")
        .text(chart_title);

    //Initiate Legend	
    var legend = svg.append("g")
        .attr("class", "legend")
        //.attr("height", 100)
        //.attr("width", 200)
        .attr('transform', 'translate(175,20)')
    ;
    //Create colour squares
    legend.selectAll('rect')
	  .data(LegendOptions)
	  .enter()
	  .append("rect")
	  .attr("x", w - 65)
	  .attr("y", function (d, i) { return i * 20; })
	  .attr("width", 10)
	  .attr("height", 10)
	  .style("fill", function (d, i) { return colorscale(i); })
    ;
    //Create text next to squares
    legend.selectAll('text')
	  .data(LegendOptions)
	  .enter()
	  .append("text")
	  .attr("x", w - 52)
	  .attr("y", function (d, i) { return i * 20 + 9; })
	  .attr("font-size", "11px")
	  .attr("fill", "#737373")
	  .text(function (d) { return d; })
    ;
}

function filterD3Chart(chart_name, chart_name2) {
    var chart_def2 = g_db[chart_name2];
    var colIndexes = [];
    for (var i = 0; i < g_db[chart_name].filters.length; i++) {
        var filter = g_db[chart_name].filters[i];
        for (var colnr = 1; colnr < chart_def2['data'][0].length; colnr++) {
            if (chart_def2['data'][0][colnr] == filter) {
                colIndexes.push(colnr);
            }
        }
    }
    if (colIndexes.length == 0) {
        colIndexes = [1, 2, 3];
    }
    d3_chart(chart_name2, chart_def2, colIndexes);
}


function getFilteredColumns(dt, filters) {
    var cols = [];
    for (var fix = 0; fix < filters.length; fix++) {
        var filter_row = filters[fix]['row'];
        var filter_value = filters[fix]['value'];
        for (var cix = 0; cix < dt.getNumberOfColumns() ; cix++) {
            var value = dt.getValue(filter_row, cix);
            var label = dt.getColumnLabel(cix);
            if (label == filter_value) {
                cols.push(cix);
                break;
            }
        }
    }
    return cols;
}

function sortColumns(dt, rownr, frozenColumns, sortAscending) {
    var sortcols = [];
    var cols = [];
    //g_db[chart_name2].view.setColumns(0, nrcols - 1);
    // first two rows are fixed
    for (var cix = frozenColumns; cix < dt.getNumberOfColumns() ; cix++) {
        var value = dt.getValue(rownr, cix);
        var item = {};
        item['colvalue'] = value;
        item['colindex'] = cix;
        sortcols.push(item);
    }
    sortcols.sort(function (a, b) {
        if (sortAscending) {
            return a['colvalue'] - b['colvalue'];
        } else {
            return b['colvalue'] - a['colvalue'];
        }
    });
    for (var cix = 0; cix < frozenColumns; cix++) {
        cols.push(cix);
    }
    for (var cix = 0; cix < sortcols.length; cix++) {
        cols.push(sortcols[cix]['colindex']);
    }
    return cols;
}

function setFilters(chart_name, categorie) {
    var found = false;
    for (var i = 0; i < g_db[chart_name].filters.length; i++) {
        var filter = g_db[chart_name].filters[i];
        if (categorie == filter) {
            g_db[chart_name].filters.splice(i, 1);
            found = true;
            break;
        }
    }
    if (!found) {
        g_db[chart_name].filters.push(categorie);
    }
}

function setRowsChart(chart_name, chart_name2) {
    var dt2 = g_db[chart_name2].datatable;
    var nrrows2 = dt2.getNumberOfRows();
    var nrcols2 = dt2.getNumberOfColumns();
    var setrows = [];
    var transpose = false;
    if ('transpose' in g_db[chart_name2]) {
        transpose = g_db[chart_name2]['transpose'];
    }
    if (g_db[chart_name].filters.length > 0) {
        if (!transpose) {
            for (var i = 0; i < g_db[chart_name].filters.length; i++) {
                var filter = g_db[chart_name].filters[i];
                var rowIndexes = dt2.getFilteredRows([{ column: 0, value: filter }]);
                setrows = setrows.concat(rowIndexes);
            }
        } else {
            var filters = [];
            for (var i = 0; i < g_db[chart_name].filters.length; i++) {
                var filter = g_db[chart_name].filters[i];
                var rowIndexes = getFilteredColumns(dt2, [{ row: 0, value: filter }]);
                setrows = setrows.concat(rowIndexes);
            }
            // make sure the labels are one of the displayed columns
            setrows = [0].concat(setrows);
        }
    } else {
        if (!transpose) {
            for (var rownr = 0; rownr < nrrows2; rownr++) {
                setrows.push(rownr);
            }
        } else {
            for (var colnr = 0; rownr < nrcols2; colnr++) {
                setrows.push(colnr);
            }
        }
    }
    return setrows;
}

function filterGoogleChart(chart_name, chart_name2) {
    var dt2 = g_db[chart_name2].datatable;
    var transpose = false;
    if ('transpose' in g_db[chart_name2]) {
        transpose = g_db[chart_name2]['transpose'];
    }
    var setrows = setRowsChart(chart_name, chart_name2);
    if (!transpose) {
        g_db[chart_name2].view.setRows(setrows);
        //g_db[chart_name2].chart_wrapper.draw();
    } else {
        //g_db[chart_name2].chart_wrapper.setDataTable(g_db[chart_name2].datatable);
        g_db[chart_name2].view.setColumns(setrows);
        //g_db[chart_name2].chart_wrapper.setView(g_db[chart_name2].view.toJSON());
        //g_db[chart_name2].chart_wrapper.draw();
        //for (var cix = 0; cix < g_db[chart_name2].control_wrappers.length; cix++) {
        //    g_db[chart_name2].google_db.bind(g_db[chart_name2].control_wrappers[cix], g_db[chart_name2].chart_wrapper);
        //}
        //g_db[chart_name2].google_db.draw(g_db[chart_name2].data);
    }
    g_db[chart_name2].google_db.draw(g_db[chart_name2].view);
}

function filterChart(chart_name, chart_name2) {
    var chdiv2 = chart_name2 + '_chdiv'
    // check whether chart2 is part of existing dashboard
    var chart_div2 = document.getElementById(chdiv2);
    if (chart_div2 != null) {
        if (g_db[chart_name2]['chart_type'] == 'RadarChart') {
            filterD3Chart(chart_name, chart_name2)
        } else {
            filterGoogleChart(chart_name, chart_name2)
        }
    }
}


function selectEventChart(chart_name, rowIndex, columnIndex, argument) {
    if (argument == 'country.keyword') {
        var field = argument;
        var select_elm = document.getElementsByName(field)[0];
        select_elm.options[rowIndex].selected = !select_elm.options[rowIndex].selected;
    }
}


function google_chart(chart_name, json_data) {
    google.charts.load('current', {'packages':['corechart', 'controls']});
    var dbdiv = chart_name + '_dbdiv'
    var chdiv = chart_name + '_chdiv'
    var ctdivs = [chart_name + '_ct1div', chart_name + '_ct2div']
    google.charts.setOnLoadCallback(drawVisualization);

    function drawVisualization() {
        // in case the X value is a date is still requires converting to a Date
        var X_facet = json_data['X_facet']
        if ("type" in X_facet) {
            if (X_facet['type'] == 'date') {
                for (var rix = 1; rix < json_data['data'].length; rix++) {
                    var s = json_data['data'][rix][0];
                    if (typeof s === 'string') {
                        var d = new Date(s);
                        json_data['data'][rix][0] = d
                    }
                }
            }
        }
        var data = google.visualization.arrayToDataTable(json_data['data']);
        var view = new google.visualization.DataView(data);
        var chart_type = json_data['chart_type'];
        var chart_title = json_data['chart_title'];
        var x_total = true
        //var y_axis = 1 // secondary axis = 1
        if ("total" in X_facet) {
            x_total = X_facet['total']
        }
        var transpose = false
        //var y_axis = 1 // secondary axis = 1
        if ("transpose" in json_data) {
            transpose = json_data['transpose']
        }
        if ("Y_facet" in json_data) {
            var Y_facet = json_data['Y_facet']
            //if ("axis" in Y_facet) {
            //    y_axis = X_facet['axis']
            //}
        }

        // Series is moved to the Chart Defition
        //var series = {};
        //var axis = 0;
        //for (var colnr=0; colnr<data.getNumberOfColumns(); colnr++) {
        //    series[colnr] = { "targetAxisIndex": axis };
        //    axis = y_axis
        //}

        var t1 = g_db[chart_name].google_db;
        var t2 = g_db[chart_name].chart_wrapper;
        if (typeof t1 === 'undefined') {
            var controls = ['StringFilter'];
            if ('controls' in json_data) {
                var controls = json_data['controls'];
                if (controls == null) {
                    controls = [];
                }
            }
            var google_db = null;
            if (controls.length > 0) {
                var google_db = new google.visualization.Dashboard(dbdiv);
            }
            var options = {
                //'title': chart_title,
                // 'series': series,
                'allowHtml': true,
                'dataMode': 'regions',
                animation: {
                    duration: 1000,
                    easing: 'out',
                    startup: true,
                }
            };
            if ('options' in json_data) {
                options = $.extend(options, json_data['options']);
            }
            if ('formatter' in json_data) {
                for (var prop in json_data['formatter']) {
                    if (prop == 'NumberFormat') {
                        var cols = json_data['formatter'][prop];
                        for (var colix in cols) {
                            var format = cols[colix];
                            var formatter = new google.visualization.NumberFormat(format);
                            colix = Number(colix);
                            formatter.format(data, colix);
                        }
                    }
                    if (prop == 'setColumnProperties') {
                        var cols = json_data['formatter'][prop];
                        for (var colix in cols) {
                            var properties = cols[colix];
                            colix = Number(colix);
                            data.setColumnProperties(colix, properties)
                            var get_properties = data.getColumnProperties(colix);
                        }
                    }
                    if (prop == 'setProperty') {
                        var cells = json_data['formatter'][prop];
                        for (var cellix=0; cellix<cells.length; cellix++) {
                            var cell = cells[cellix];
                            data.setProperty(cell[0], cell[1], cell[2], cell[3])
                            var get_properties = data.getProperty(cell[0], cell[1], cell[2]);
                        }
                    }
                }
            }
            var chart_wrapper = new google.visualization.ChartWrapper({
                chartType: chart_type,
                // dataTable: data,
                options : options,
                containerId: chdiv
            });
            chart_wrapper.setChartName(chart_name);
            var control_wrappers = [];

            for (var cix = 0; cix < controls.length; cix++) {
                var control = controls[cix];
                if (control == 'StringFilter') {
                    var control_wrapper = new google.visualization.ControlWrapper({
                        'controlType': 'StringFilter',
                        'containerId': ctdivs[cix],
                        'options': {
                            'filterColumnIndex': 0
                        }
                    });
                } else if (control == 'CategoryFilter') {
                    var label = X_facet['label'];
                    if (transpose) {
                        label = Y_facet['label'];
                    }
                    var control_wrapper = new google.visualization.ControlWrapper({
                        'controlType': 'CategoryFilter',
                        'containerId': ctdivs[cix],
                        'options': {
                            'filterColumnIndex': 0,
                            'ui': {
                                'labelStacking': 'vertical',
                                'label': label,
                                'allowTyping': true,
                                'allowMultiple': true
                            }
                        }
                    });
                } else if (control == 'NumberRangeFilter') {
                    //var label = data.getValue(0, 0);
                    var label = data.getColumnLabel(1);
                    var control_wrapper = new google.visualization.ControlWrapper({
                        'controlType': 'NumberRangeFilter',
                        'containerId': ctdivs[cix],
                        'options': {
                            'filterColumnIndex': 1,
                            //'minValue': 0.0,
                            //'maxValue': 10.0,
                            'ui': {
                                'orientation': 'horizontal',
                                'label': label,
                                //'unitIncrement': 0.1,
                                //'blockIncrement' : 0.1,
                                'step' : 0.1,
                                'ticks': 10,
                                'showRangeValues': true,
                            }
                        }
                    });
                } else if (control == 'DateRangeFilter') {
                    //var label = data.getValue(0, 0);
                    var label = data.getColumnLabel(0);
                    var control_wrapper = new google.visualization.ControlWrapper({
                        'controlType': 'DateRangeFilter',
                        'containerId': ctdivs[cix],
                        'options': {
                            'filterColumnIndex': 0,
                            //'minValue': 0.0,
                            //'maxValue': 10.0,
                            'ui': {
                                'orientation': 'horizontal',
                                'label': label,
                                //'unitIncrement': 0.1,
                                //'blockIncrement' : 0.1,
                                'step': 0.1,
                                'ticks': 10,
                                'showRangeValues': true,
                            }
                        }
                    });
                } else if (control == 'ChartRangeFilter') {
                    //var label = data.getValue(0, 0);
                    var label = data.getColumnLabel(0);
                    var date_end = new Date();
                    var date_begin = new Date(date_end.getFullYear()-1, 0, 1) 

                    var control_wrapper = new google.visualization.ControlWrapper({
                        'controlType': 'ChartRangeFilter',
                        'containerId': ctdivs[cix],
                        'options': {
                            'filterColumnIndex': 0,
                            //'minValue': 0.0,
                            //'maxValue': 10.0,
                            'ui': {
                                'orientation': 'horizontal',
                                'label': label,
                                //'unitIncrement': 0.1,
                                //'blockIncrement' : 0.1,
                                'showRangeValues': true,
                                chartOptions: {
                                    height: 50,
                                    hAxis: {
                                        format: 'yy/MMM'
                                    }
                                }
                            }
                        },
                        'state': {
                            'range': {
                                'start': date_begin,
                                'end': date_end
                            }
                        }
                    });
                    //document.getElementById(ctdivs[cix]).style.height = "50px";
                }
                control_wrappers.push(control_wrapper);
            }
            if ('listener' in json_data) {
                var tempListener = google.visualization.events.addOneTimeListener(chart_wrapper, 'ready', function () {
                    var listener = json_data['listener'];
                    g_db[chart_name].filters = [];
                    g_db[chart_name].setrows = [];
                    g_db[chart_name].sortrows = {};
                    for (var event_name in listener) {
                        if (event_name == 'sort') {
                            google.visualization.events.addListener(chart_wrapper.getChart(), 'sort', function (ev) {
                                var chart_name = chart_wrapper.getChartName();
                                var chart = chart_wrapper.getChart();
                                var dt = chart_wrapper.getDataTable();

                                var columnIndex = ev['column'];
                                //var categorie = dt.getColumnLabel(columnIndex)
                                var categorie = g_db[chart_name].view.getColumnLabel(columnIndex)
                                //var rowIndexes = g_db['cand_emotion_col'].view.getFilteredRows([{ column: 0, value: categorie }]);
                                setFilters(chart_name, categorie)
                                var charts2 = g_db[chart_name]['listener']['sort'];
                                for (var charts2_ix = 0; charts2_ix < charts2.length; charts2_ix++) {
                                    var chart_name2 = charts2[charts2_ix];
                                    filterChart(chart_name, chart_name2);
                                }
                            });
                        }
                        if (event_name == 'select') {
                            google.visualization.events.addListener(chart_wrapper.getChart(), 'select', function (ev) {
                                var chart_name = chart_wrapper.getChartName();
                                var chart = chart_wrapper.getChart();
                                var listen = g_db[chart_name]['listener']['select'];
                                // getDataTable returns the view, for sorting we use the original datatable
                                var dt = chart_wrapper.getDataTable();
                                var selection = chart.getSelection();
                                for (var i = 0; i < selection.length; i++) {
                                    var item = selection[i];
                                    var columnIndex = item.column;
                                    var rowIndex = item.row;
                                    for (var action in listen) {
                                        var sort_arg = listen[action];
                                        if (action == 'rowsort' && rowIndex != null && columnIndex == null) {
                                            var rowlabel = dt.getValue(rowIndex, 0);
                                            var sortAscending = false;
                                            if (rowlabel in g_db[chart_name].sortrows) {
                                                sortAscending = !g_db[chart_name].sortrows[rowlabel];
                                            }
                                            g_db[chart_name].sortrows[rowlabel] = sortAscending;
                                            var setcols = sortColumns(g_db[chart_name].datatable, rowIndex, 2, sortAscending);
                                            g_db[chart_name].view.setColumns(setcols);
                                            // make view effective for not topline???
                                            for (var cix = 0; cix < g_db[chart_name].control_wrappers.length; cix++) {
                                                g_db[chart_name].google_db.bind(g_db[chart_name].control_wrappers[cix], g_db[chart_name].chart_wrapper);
                                            }
                                            if (g_db[chart_name].google_db != null) {
                                                g_db[chart_name].google_db.draw(g_db[chart_name].view);
                                            } else {
                                                g_db[chart_name].chart_wrapper.setView(g_db[chart_name].view.toJSON());
                                                g_db[chart_name].chart_wrapper.draw();
                                            }
                                        }
                                        if (action == 'colsort' && rowIndex == null && columnIndex != null) {
                                            if (sort_arg == 'categories') {
                                                columnIndex = 0;
                                            }
                                            var columnlabel = dt.getColumnLabel(columnIndex);
                                            var sortAscending = false;
                                            if (columnlabel in g_db[chart_name].sortrows) {
                                                sortAscending = !g_db[chart_name].sortrows[columnlabel];
                                            }
                                            g_db[chart_name].sortrows[columnlabel] = sortAscending;
                                            var setrows = g_db[chart_name].datatable.getSortedRows({ 'column': columnIndex, 'desc': !sortAscending });
                                            g_db[chart_name].view.setRows(setrows);
                                            //g_db[chart_name].chart_wrapper.draw();
                                            if (g_db[chart_name].google_db != null) {
                                                g_db[chart_name].google_db.draw(g_db[chart_name].view);
                                            } else {
                                                g_db[chart_name].chart_wrapper.setView(g_db[chart_name].view.toJSON());
                                                g_db[chart_name].chart_wrapper.draw();
                                            }
                                        }
                                        if (action == 'rowcolfilter' && rowIndex != null && columnIndex != null) {
                                            var rowlabel = dt.getValue(rowIndex, 0);
                                            setFilters(chart_name, rowlabel)
                                            var charts2 = listen[action];
                                            for (var charts2_ix = 0; charts2_ix < charts2.length; charts2_ix++) {
                                                var chart_name2 = charts2[charts2_ix];
                                                filterChart(chart_name, chart_name2);
                                            }
                                        }
                                        if (action == 'select_event') {
                                            var argument = listen[action];
                                            selectEventChart(chart_name, rowIndex, columnIndex, argument);

                                        }
                                    }
                                }
                            });
                        }
                    }
                });
            }
            g_db[chart_name].google_db = google_db;
            g_db[chart_name].chart_wrapper = chart_wrapper;
            g_db[chart_name].control_wrappers = control_wrappers;
            g_db[chart_name].datatable = data;
            g_db[chart_name].view = view

            if (controls.length > 0) {
                for (var cix = 0; cix < controls.length; cix++) {
                    google_db.bind(control_wrappers[cix], chart_wrapper);
                }
                g_options = {
                    allowHtml   : true,
                    animation   : {
                        duration    : 1000,
                        easing      : 'out',
                        startup     : true,
                    }
                }
                g_db[chart_name].google_db.draw(view, g_options);
            } else {
                g_db[chart_name].chart_wrapper.setDataTable(data);
                g_db[chart_name].chart_wrapper.setView(view.toJSON());
                g_db[chart_name].chart_wrapper.draw();
            }

        }

        // chart_wrapper.draw();
        //g_db[chart_name].google_db.draw(data, g_options);
        //google_db.draw(data);
    }
}

function category_keyword_table(json_data) {
    google.charts.load('current');
    google.charts.setOnLoadCallback(drawVisualization);

    function drawVisualization() {
        var data = google.visualization.arrayToDataTable(json_data['data']);
        var chart_type = json_data['chart_type'];
        var wrapper = new google.visualization.ChartWrapper({
            chartType: chart_type,
            dataTable: data,
            options: { 'title': 'Categories / Keywords' },
            containerId: 'category_keyword_table_div'
        });
        wrapper.draw();
    }
}

function sentiment_pie(json_data) {
    //    var touchdowns = resp.aggregations.touchdowns.buckets;
    // d3 donut chart
    if ('facet_keyword' in json_data) {
        var data = json_data['facet_keyword']
        var width = 600,
            height = 300,
            radius = Math.min(width, height) / 2;
        var color = ['#ff7f0e', '#d62728', '#2ca02c', '#1f77b4'];
        var arc = d3.svg.arc()
            .outerRadius(radius - 60)
            .innerRadius(20);
        var pie = d3.layout.pie()
            .sort(null)
            .value(function (d) { return d.doc_count; });
        var svg = d3.select("#donut-chart").append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", "translate(" + width / 1.4 + "," + height / 2 + ")");
        var g = svg.selectAll(".arc")
            .data(pie(data))
            .enter()
            .append("g")
                .attr("class", "arc")
        ;
        g.append("path")
            .attr("d", arc)
            .style("fill", function (d, i) { return color[i]; });
        g.append("text")
            .attr("transform", function (d) { return "translate(" + arc.centroid(d) + ")"; })
            .attr("dy", ".35em")
            .style("text-anchor", "middle")
            .style("fill", "white")
            .text(function (d) { return d.data.key; });
    }
}


