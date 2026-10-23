
//----- عند الضغط على سجل في الفهرس
function treeViewClickHandler(itemId, el)
{
    $("#TreeViewID").val(itemId);

    var fehresID = $("#TV_Li_FehresRec_" + itemId).attr("data-fehresId");
    $("#TreeViewFehresID").val(fehresID);

    $("div.no-child").removeClass("add_background_color");
    $(el).parent().addClass("add_background_color");

    getFehresRelated();
}



//---- Tree View Collapse All Rec.
function treeViewCollapseAll() {
    $("img.plus-minus").trigger("click")
}

//---- Tree View Expand All Rec.
function treeViewExpandAll()
{
    getFehres(true);
}



//---- Tree View Print
function treeViewPrint() {
    var style = "<style>\
            ul, li {\
                list-style: none;\
                margin: 0;\
                padding: 0;\
            }\
            \
            body {\
                direction: rtl;\
            }\
            \
            ul {\
                padding-right: 1.5em;\
                font-family: 'Trebuchet MS', sans-serif;\
                font-size: small;\
            }\
            \
            li {\
                padding-right: 1em;\
                border: 1px dotted black;\
                border-width: 0 1px 0 0;\
            }\
            \
                li.container {\
                    border-bottom: 0px;\
                }\
        </style>";
    var htmlContent = "";
    htmlContent += "<html>";
    htmlContent += "<head>";
    htmlContent += "<title>Print</title>";
    htmlContent += style;
    htmlContent += "</head>";
    htmlContent += "<body>";
    htmlContent += $("#myTreeViewHTML").html();
    htmlContent += "</body>";
    htmlContent += "</html>";
    var myWindow = window.open("", "", "width=500, height=500, location=no, toolbar=no");
    myWindow.document.write(htmlContent);
    myWindow.print();
}



