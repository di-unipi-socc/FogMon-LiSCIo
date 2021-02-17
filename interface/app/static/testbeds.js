htmlSessionSpec = `
<div class="container"><button class="btn btn-outline-primary" id="accuracy">Accuracy</button></div> </br>
<table id="table-accuracy" class="table table-striped">
    <thead>
        <tr>
            <th>Moment</th>
            <th>Latency intra</th>
            <th>Latency inter</th>
            <th>Bandwidth intra</th>
            <th>Bandwidth inter</th>
            <th>Performance (sec)</th>
        </tr>
    </thead>
    <tbody>
    </tbody>
</table>
<div class="container"><button class="btn btn-outline-primary" id="footprint">Footprint</button></div> </br>
<table id="table-footprint" class="table table-striped">
    <thead>
        <tr>
            <th>mean cpu</th>
            <th>mean mem</th>
            <th>mean tx</th>
            <th>mean rx</th>
        </tr>
    </thead>
    <tbody>
    </tbody>
</table>
<table id="table-footprint2" class="table table-striped">
    <thead>
        <tr>
            <th>peak cpu</th>
            <th>min cpu</th>
            <th>peak mem</th>
            <th>min mem</th>
            <th>peak tx</th>
            <th>min tx</th>
            <th>peak rx</th>
            <th>min rx</th>
        </tr>
    </thead>
    <tbody>
    </tbody>
</table>
`

htmlNoData = `
<h4>No Data</h4>
`

htmlSession = `
data...
`

function getSession(id, spec) {
    $("#session").empty();
    var request = $.ajax({
        url: "/testbed/"+id,
        method: "GET",
        dataType: "json"
    });
    
    request.done(function( msg ) {
        $("#session").empty();
        if (spec) {
            $("#session").attr("session",id);
            $("#session").append(htmlSessionSpec);
        }else {
            $("#session").attr("session",id);
            $("#session").append(htmlSessionSpec);
        }
    });
    
    request.fail(function( jqXHR, textStatus ) {
        $("#session").empty();
        $("#session").append(htmlNoData);
    });
}

function getAccuracy(id) {
    var request = $.ajax({
        url: "/testbed/"+id+"/accuracy",
        method: "GET",
        dataType: "json"
    });
    
    request.done(function( msg ) {
        $("#table-accuracy > tbody").empty()
        msg["data"].forEach((data, i) => {
            element = `
            <tr>
                <th>${i}</th>
                <td>${data["L"]["intra"]["mean"].toFixed(2)}</td>
                <td>${data["L"]["inter"]["mean"].toFixed(2)}</td>
                <td>${data["B"]["intra"]["mean"].toFixed(2)}</td>
                <td>${data["B"]["inter"]["mean"].toFixed(2)}</td>
                <td>${data["time"]}</td>
            </tr>
            `;
            $("#table-accuracy > tbody").append(element)
        });
    });
    
    request.fail(function( jqXHR, textStatus ) {
        alert( "Request failed: " + textStatus );
    });
}

function getFootprint(id) {
    var request = $.ajax({
        url: "/testbed/"+id+"/footprint",
        method: "GET",
        dataType: "json"
    });
    
    request.done(function( msg ) {
        $("#table-footprint > tbody").empty()
        $("#table-footprint2 > tbody").empty()
        data = msg["data"]
        element = `
        <tr>
            <td>${data["cpu"]["mean"].toFixed(2)}%</td>
            <td>${data["mem"]["mean"].toFixed(2)}MB</td>
            <td>${data["tx"]["mean"].toFixed(2)}B/s</td>
            <td>${data["rx"]["mean"].toFixed(2)}B/s</td>
        </tr>
        `;
        $("#table-footprint > tbody").append(element)
        element = `
        <tr>
            <td>${data["cpu"]["max"].toFixed(2)}%</td>
            <td>${data["cpu"]["min"].toFixed(2)}%</td>
            <td>${data["mem"]["max"].toFixed(2)}MB</td>
            <td>${data["mem"]["min"].toFixed(2)}MB</td>
            <td>${data["tx"]["max"].toFixed(2)}B/s</td>
            <td>${data["tx"]["min"].toFixed(2)}B/s</td>
            <td>${data["rx"]["max"].toFixed(2)}B/s</td>
            <td>${data["rx"]["min"].toFixed(2)}B/s</td>
        </tr>
        `;
        $("#table-footprint2 > tbody").append(element)
    });
    
    request.fail(function( jqXHR, textStatus ) {
        alert( "Request failed: " + textStatus );
    });
}

$(document).ready(function(){
    $("#sessions").on('click', 'tbody > tr', function() {
        var id = $(this).attr("session");
        var spec = parseInt($(this).attr("spec"));
        getSession(id, spec);
    });

    $("#session").on('click', "#accuracy",function() {
        var id = $("#session").attr("session");
        getAccuracy(id);
    });
    $("#session").on('click', "#footprint",function() {
        var id = $("#session").attr("session");
        getFootprint(id);
    });
});
