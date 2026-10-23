

//------ الحصول على عناصر الفهرس
function getFehres(loadAll)
{

    var FehrID = $("#MainFehrersID").val();
    var RecType = $("#recType").val();
    var RecID = $("#recID").val();
    var Where = $("#inputWhereText").val();

    var myURL = '/Tash/GetTashFehres';

    $.ajax({
        type: "GET",
        url: myURL,
        data: { FehrID: FehrID, RecType: RecType, RecID: RecID, Where: Where, loadAll: loadAll, SearchMawaad: false },
        success: function (result) {
            $("#myTreeViewHTML").html(result);

             loadChildOnLoad();
             var myId = $("li.no-child:first").attr("data-recId");
             if (myId > 0) treeViewClickHandler(myId, $("#TV_NoChildSpan_" + myId));
        }
    });
}


function loadChildOnLoad() {

    var FehrID = $("#MainFehrersID").val();
    var RecType = $("#recType").val();
    var RecID = $("#recID").val();
    var Where = $("#inputWhereText").val();

    var myURL = '/Tash/GetTashFehresWithParentID';

    var firstClosedParent = $("img.plus-minus[src$='plus_zps8o4adn0e.gif']:first");
    var ulList = $(firstClosedParent).parent().next();
    var parentId = $(firstClosedParent).attr("data-parentId");
    $("#TV_Span_" + parentId).addClass('Font_color_Red');
    $(firstClosedParent).attr("src", $(firstClosedParent).attr("data-minus"));
    $(firstClosedParent).next().attr("src", $(firstClosedParent).next().attr("data-open"));
    $.get(myURL, { FehrID: FehrID, RecType: RecType, RecID: RecID, Where: Where, ParentId: parentId }).done(function (ui) {
        ulList.html(ui);
        var isChild = $("ul", $("li:first", ulList)).length === 0;
        if (!isChild) {
            loadChildOnLoad();
        } else {
            var myId = $("li.no-child:first").attr("data-recId");
            treeViewClickHandler(myId, $("#TV_NoChildSpan_" + myId));
        }
    });
}



//------ فتح أو غلق أحد آباء الفهرس 
function toggleTreeView(el)
{
    var parentId = $(el).attr("data-parentId");

    var FehrID = $("#MainFehrersID").val();
    var RecType = $("#recType").val();
    var RecID = $("#recID").val();
    var Where = $("#inputWhereText").val();

    var myURL = '/Tash/GetTashFehresWithParentID';

    var ulList   = $(el).parent().next();

    if ($(el).attr("src") === $(el).attr("data-minus"))
    {
        $("#TV_Span_" + parentId).removeClass('Font_color_Red');
        ulList.hide();
        $(el).attr("src", $(el).attr("data-plus"));
        $(el).next().attr("src", $(el).next().attr("data-close"));
    }
    else
    {

        $("#TV_Span_" + parentId).addClass('Font_color_Red'); 
        if ($("li", ulList).length == 0)
        {
            $.get(myURL, { FehrID: FehrID, RecType: RecType, RecID: RecID, ParentId: parentId, Where: Where, SearchMawaad: false }).done(function (ui) { ulList.html(ui); });
        }
        $(el).attr("src", $(el).attr("data-minus"));
        $(el).next().attr("src", $(el).next().attr("data-open"));
        $(ulList).show();
    }
}




//------ الوصول للمادة تبعاً للفهرس 
function OpenFehresRec() {
    var FehresID =  $("#TreeViewFehresID").val();

    var targetElement = $("#FullPathID_" + FehresID);
    if (targetElement.length > 0) {
        $([document.documentElement, document.body]).animate({
            scrollTop: targetElement.offset().top
        }, 100);
        $('#TashFehres').modal('hide');
    };
}



function getFehresRelated() {
    var FehresID = $("#TreeViewFehresID").val();

    var targetElement = $("#FullPathID_" + FehresID);
    //if (targetElement.length > 0) {
    //    $([document.documentElement, document.body]).animate({
    //        scrollTop: targetElement.offset().top
    //    }, 100);
    //    $('#TashFehres').modal('hide');
    //};
}