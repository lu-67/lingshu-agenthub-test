/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 99.6078431372549, "KoPercent": 0.39215686274509803};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.9254901960784314, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "R3 定时任务列表"], "isController": false}, {"data": [1.0, 500, 1500, "R4 当前用户信息"], "isController": false}, {"data": [0.36666666666666664, 500, 1500, "04 发目标 send（核心压测点）"], "isController": false}, {"data": [1.0, 500, 1500, "W1 新建智能体"], "isController": false}, {"data": [1.0, 500, 1500, "R0 登录 admin"], "isController": false}, {"data": [1.0, 500, 1500, "W2 新建会话"], "isController": false}, {"data": [1.0, 500, 1500, "02 智能体列表（取第一个 id）"], "isController": false}, {"data": [1.0, 500, 1500, "W0 登录 admin"], "isController": false}, {"data": [1.0, 500, 1500, "W4 新建定时任务"], "isController": false}, {"data": [1.0, 500, 1500, "05 会话详情"], "isController": false}, {"data": [0.36666666666666664, 500, 1500, "W3 发目标 send"], "isController": false}, {"data": [1.0, 500, 1500, "06 定时任务列表"], "isController": false}, {"data": [1.0, 500, 1500, "R2 会话列表"], "isController": false}, {"data": [1.0, 500, 1500, "03 建会话"], "isController": false}, {"data": [1.0, 500, 1500, "R1 智能体列表"], "isController": false}, {"data": [1.0, 500, 1500, "01 登录 tester"], "isController": false}, {"data": [1.0, 500, 1500, "R5 平台总统计"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 255, 1, 0.39215686274509803, 250.60000000000008, 9, 3064, 75.0, 1154.4, 1360.9999999999998, 2804.039999999999, 36.29893238434163, 50.279415035587185, 15.082156361209965], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["R3 定时任务列表", 15, 0, 0.0, 36.86666666666667, 9, 233, 22.0, 119.60000000000007, 233.0, 233.0, 6.41025641025641, 0.8951822916666667, 2.391326121794872], "isController": false}, {"data": ["R4 当前用户信息", 15, 0, 0.0, 29.799999999999997, 14, 49, 30.0, 47.2, 49.0, 49.0, 6.4963187527068, 1.5635996372888696, 2.398055164573408], "isController": false}, {"data": ["04 发目标 send（核心压测点）", 15, 1, 6.666666666666667, 1553.2666666666667, 1115, 3064, 1332.0, 2753.8, 3064.0, 3064.0, 2.267230955259976, 8.27627862379081, 1.1535423121977026], "isController": false}, {"data": ["W1 新建智能体", 15, 0, 0.0, 56.33333333333333, 20, 92, 57.0, 92.0, 92.0, 92.0, 2.7726432532347505, 1.0505718576709797, 1.5000433225508318], "isController": false}, {"data": ["R0 登录 admin", 15, 0, 0.0, 130.2, 88, 277, 111.0, 259.0, 277.0, 277.0, 5.692599620493358, 1.9790678368121444, 2.17178605313093], "isController": false}, {"data": ["W2 新建会话", 15, 0, 0.0, 100.86666666666666, 33, 261, 93.0, 199.20000000000005, 261.0, 261.0, 2.7432333577176298, 0.8197552807242137, 1.2082014104791514], "isController": false}, {"data": ["02 智能体列表（取第一个 id）", 15, 0, 0.0, 60.46666666666666, 15, 127, 63.0, 112.00000000000001, 127.0, 127.0, 2.7467496795458706, 10.069627243178905, 1.0193016388939755], "isController": false}, {"data": ["W0 登录 admin", 15, 0, 0.0, 140.33333333333334, 94, 247, 135.0, 199.00000000000003, 247.0, 247.0, 2.6824034334763946, 0.932554318669528, 1.0233648515736768], "isController": false}, {"data": ["W4 新建定时任务", 15, 0, 0.0, 77.33333333333333, 28, 158, 69.0, 153.2, 158.0, 158.0, 4.123144584936778, 1.0670247216877407, 2.1904205607476634], "isController": false}, {"data": ["05 会话详情", 15, 0, 0.0, 99.73333333333335, 21, 159, 121.0, 152.4, 159.0, 159.0, 4.076086956521739, 17.156186311141305, 1.5364937160326086], "isController": false}, {"data": ["W3 发目标 send", 15, 0, 0.0, 1578.5333333333335, 1100, 2995, 1340.0, 2790.4, 2995.0, 2995.0, 2.2813688212927756, 8.10732533269962, 1.0783032319391634], "isController": false}, {"data": ["06 定时任务列表", 15, 0, 0.0, 37.266666666666666, 11, 98, 35.0, 84.2, 98.0, 98.0, 4.246885617214042, 0.5930709406851642, 1.5967294556908267], "isController": false}, {"data": ["R2 会话列表", 15, 0, 0.0, 25.733333333333334, 10, 51, 22.0, 46.2, 51.0, 51.0, 6.353240152477763, 13.160637706480303, 2.4072824015247773], "isController": false}, {"data": ["03 建会话", 15, 0, 0.0, 114.06666666666668, 37, 265, 118.0, 212.80000000000004, 265.0, 265.0, 2.7105168052041924, 0.7782147858691724, 1.1779101350740875], "isController": false}, {"data": ["R1 智能体列表", 15, 0, 0.0, 26.866666666666664, 11, 71, 22.0, 59.60000000000001, 71.0, 71.0, 6.28140703517588, 21.101601758793972, 2.3125883322864325], "isController": false}, {"data": ["01 登录 tester", 15, 0, 0.0, 128.8, 65, 250, 129.0, 191.20000000000005, 250.0, 250.0, 2.6647717178895007, 0.9394361232012791, 1.0270474329365784], "isController": false}, {"data": ["R5 平台总统计", 15, 0, 0.0, 63.73333333333332, 32, 100, 53.0, 95.2, 100.0, 100.0, 6.493506493506494, 1.5980113636363635, 2.4223823051948052], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["The operation lasted too long: It took 3,064 milliseconds, but should not have lasted longer than 3,000 milliseconds.", 1, 100.0, 0.39215686274509803], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 255, 1, "The operation lasted too long: It took 3,064 milliseconds, but should not have lasted longer than 3,000 milliseconds.", 1, "", "", "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["04 发目标 send（核心压测点）", 15, 1, "The operation lasted too long: It took 3,064 milliseconds, but should not have lasted longer than 3,000 milliseconds.", 1, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
