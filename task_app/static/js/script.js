fetch('/dashboard/api/geonetwork/metadatas.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#table');
        var xxdata = [];
        if(mydata.length == 0) {
            $table.remove();
            $('#mdtitle').remove();
            return;
        }
        $('#mdtitle').text(mydata.length + ' metadatas');
        mydata.forEach(function (value) {
            value['dhlink']='<a href="/datahub/dataset/' + value['_id'] + '">voir</a>';
            value['editlink']='<a href="/geocat/srv/fre/catalog.edit#/metadata/' + value['gnid'] +'?redirectUrl=catalog.edit">editer</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    });

fetch('/dashboard/api/mapstore/maps.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#mapstable');
        var xxdata = [];
        res = mydata['results'];
        if(mydata['totalCount'] == 0) {
            $table.remove();
            $('#mapstitle').remove();
            return;
        }
        $('#mapstitle').text(mydata['totalCount'] + ' maps');
        res.forEach(function (value) {
            id = value['id'];
            value['id'] = '<a href="/dashboard/map/' + id + '">' + id + '</a>';
            value['viewlink']='<a href="/mapstore/#/viewer/' + id + '">voir</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    });

fetch('/dashboard/api/mapstore/contexts.json')
    .then(response => response.json())
    .then(mydata => {
        var $table = $('#ctxtable');
        var xxdata = [];
        res = mydata['results'];
        if(mydata['totalCount'] == 0) {
            $table.remove();
            $('#ctxtitle').remove();
            return;
        }
        $('#ctxtitle').text(mydata['totalCount'] + ' contexts');
        res.forEach(function (value) {
            id = value['id'];
            value['id'] = '<a href="/dashboard/context/' + id + '">' + id + '</a>';
            value['viewlink']='<a href="/mapstore/#/context/' + value['name'] + '">voir</a>';
            value['editlink']='<a href="/mapstore/#/context-creator/' + id + '">editer</a>';
            xxdata.push(value);
        });
        $(function() {
            $table.bootstrapTable({data: xxdata});
        });
    });
