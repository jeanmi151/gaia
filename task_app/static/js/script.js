const fetchForHome = () => {
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
}

const DisplayPrev = (type, resid, taskids) => {
    const sorted = taskids.sort((a,b)=>new Date(b['finished']) - new Date(a['finished']));
    const arr = sorted.map(t => {
        const link = $("<a>");
        link.attr("id", 'display-taskres-' + t['id'])
        link.attr("href","javascript:PollTaskRes('" + type +"',"+ resid + ",'" + t['id'] + "');");
        link.attr("title","Show result for task " + t['id']);
        link.text("check at " + t['finished']);
        return link[0];
    });
    $('#previouslist').html(ArrayToHtmlList(arr));
}

const ArrayToHtmlList = (array) => {
  const list = $('<ul>').append(
    array.map(p => $("<li>").html(p))
  );
  return list;
}

const DeleteTask = (taskid) => {
  fetch('/dashboard/tasks/forget/' + taskid)
    .then(response => {
      if (response.status != 403) {
        $('#display-taskres-' + taskid).parent().remove();
      }
    });
}

const CheckRes = (type, resid) => {
  fetch('/dashboard/tasks/check/' + type + '/' + resid + '.json')
    .then(response => response.json())
    .then(mydata => {
        $('#pbtitle').text("En cours d'analyse");
        PollTaskRes(type, resid, mydata["result_id"]);
    });
}

const PollTaskRes = (type, resid, taskid) => {
    const poll = () => {
        fetch('/dashboard/tasks/result/' + taskid)
            .then(response => response.json())
            .then(data => {
//                console.log(data)
                if (data === null) {
                  $('#pbtitle').text('got null, shouldnt happen ?');
                } else if(!data["ready"]) {
                  $('#pbtitle').text('Waiting');
                  setTimeout(poll, 500)
                } else if (!data["successful"]) {
                  $('#problems').text('Something crashed, check browser console');
                  console.error(data)
                } else {
                  if (data["value"].problems.length > 0) {
                    $('#pbtitle').text('Problems');
                    $('#problems').html(ArrayToHtmlList(data["value"].problems));
                  } else {
                    $('#pbtitle').text('No problemo! in ' + type + ' owned by '+data["value"].owner);
                    $('#problems').remove();
                  }
                  const d = new Date(data["finished"] * 1000);
                  $('#details').text('details for ' + type + ' ' + resid + ', valid at '+ d);
                }
            })
    }
    poll();
}
