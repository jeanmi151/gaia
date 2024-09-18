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

const DisplayPrev = (type, resid, taskids, showdelete, targetdivid = '#previouslist') => {
    if (taskids === null) { return ; }
    const sorted = taskids.sort((a,b)=>new Date(b['finished']) - new Date(a['finished']));
    const arr = sorted.map(t => {
        const link = $("<a>");
        link.attr("id", 'display-taskres-' + t['id'])
        link.attr("href","javascript:PollTaskRes('" + type +"','"+ resid + "','" + t['id'] + "');");
        link.attr("title","Show result for task " + t['id']);
        link.text("check at " + t['finished']);
        if (showdelete) {
          const link2 = $("<a>");
          link2.attr("href","javascript:DeleteTask('" + t['id'] + "');");
          link2.attr("title","Forget result for task " + t['id']);
          link2.html('<i class="bi bi-trash"></i>');
          return [ link[0], "&nbsp;", link2[0] ];
        }
        return link[0];
    });
    $(targetdivid).html(ArrayToHtmlList(arr));
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

const CheckRes = (type, resid, targetdivid = '#pbtitle') => {
  fetch('/dashboard/tasks/check/' + type + '/' + resid + '.json')
    .then(response => response.json())
    .then(mydata => {
        $(targetdivid).text("En cours d'analyse");
        PollTaskRes(type, resid, mydata["result_id"], targetdivid);
    });
}

const PollTaskRes = (type, resid, taskid, targetdivid = '#pbtitle') => {
    const poll = () => {
        const targetpbdivid = targetdivid.replace('#pbtitle', '#problems')
        const targetpbdetdivid = targetdivid.replace('#pbtitle', '#pbdetails')
        fetch('/dashboard/tasks/result/' + taskid)
            .then(response => response.json())
            .then(data => {
//                console.log(data)
                if (data === null) {
                  $(targetdivid).text('got null, shouldnt happen ?');
                } else if(!data["ready"]) {
                  if (data['completed'] !== null) {
                    $(targetdivid).text(data["completed"]);
                  } else {
                    $(targetdivid).text('Waiting');
                  }
                  setTimeout(poll, 500)
                } else if (!data["successful"]) {
                  $(targetpbdivid).text('Something crashed, check browser console');
                  console.error(data)
                } else {
                  if (Array.isArray(data["value"])) {
                      var p = data['value'].filter(function(f) {
                        return f['problems'].length > 0
                      });
                      const probs = p.map(j => {
                        return j.problems.map(i => {
                          return j.args + ' has this issue: ' + i
                        })
                      });
                      data["value"].problems = probs.flat(1)
                  }
                  if (data["value"].problems.length > 0) {
                    $(targetdivid).text('Problems');
                    $(targetpbdivid).html(ArrayToHtmlList(data["value"].problems));
                  } else {
                    $(targetdivid).text('No problemo! in ' + type + ' owned by '+data["value"].owner);
                    $(targetpbdivid).empty();
                  }
                  const d = new Date(data["finished"] * 1000);
                  $(targetpbdetdivid).text('dernière vérification faite le '+ d);
                }
            })
    }
    poll();
}

const SendToMapstore = (type, url, layername) => {
    const msurl="/mapstore/#/?actions=[{\"type\":\"CATALOG:ADD_LAYERS_FROM_CATALOGS\",\"layers\":[\"" + layername + "\"],\"sources\":[{\"type\":\"" + type + "\",\"url\":\"" + url + "\"}]}]";
    window.open(msurl, "_blank");
}
