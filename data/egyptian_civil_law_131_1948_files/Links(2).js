//------- مسح واخفاء النص
function clearText(id, recType) {
    $("#hidden_" + recType + "_" + id).html('');
    $("#hidden_" + recType + "_" + id).addClass("hidden");
}

//------ فتح نص كامل 
function openAngloFullText(Id, ColorText, Slug) {
    var data =
    {
        id: Id,
        type: 1
    }

    if (ColorText !== '') {
        data.search = ColorText;
    }

    var params = jQuery.param(data)

    var url = `/full-text-anglo-saxon-judgments/${Slug}?${params}`;
    window.open(url, '_blank');
}




//------ فتح من الاتباطات الجانبية  
function openAngloSak(id) {
    var data =
    {
        id: id,
        type: 1
    }
    var params = jQuery.param(data)

    var url = "/full-text-anglo-saxon-judgments?" + params;
    window.open(url, '_blank');
}



//------ فتح نص كامل بالفهرس
function openAngloIndex(Id, Tit, ColorText) {
    var data =
    {
        var1: Id,
        var2: Tit,
        var3: ColorText
    }
    var params = jQuery.param(data)

    var url = "/anglo-saxon-judgment?" + params;
    window.open(url, '_blank');
}


//-------  التشريعات المرتبطة 
function showAngloTash(id, recType) {

    var myType = 6;
    if (recType == 2) { myType = 7; }
    var data =
    {
        var0: myType,
        var1: recType,
        var2: id,
        var3: "Referenced Legislation: " + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: null,
        var5: 2
    }
    var params = jQuery.param(data)

    var url = "/referenced-legislation?" + params;
    window.open(url, '_blank');
}




//--------  المواد المرتبطة 
function showAngloMawaad(id, recType) {
    $.ajax({
        type: "GET",
        url: "/Tash/AngloRelatedTash",
        data: { RecID: id, RecType: recType },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");

            $("#RelatedTashTable_" + id + "_" + recType + ">tbody>tr:first").trigger('click');
        }
    });
}


//------ نصوص المواد التشريعية المرتبطة في نفس الشاشة   
function getAngloRelatedTashMawaadListIn(RecID, RecType, TashID) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetAngloRelatedMawaadByTashID",
        data: { RecID: RecID, RecType: RecType, TashID: TashID },
        success: function (ui) {
            $("#AngloRelatedTashMawaadTextIn" + RecID + "_" + RecType).html(ui);
            $("#RelatedTashTable_" + RecID + "_" + RecType + "> tbody>tr").removeClass('tr_active');
            $("#RelatedTashB_" + RecID + "_" + RecType + "_" + TashID).addClass("tr_active");

            //$("#AhRelatedTashMawaadTextIn" + RecID + "_" + RecType).animate({ scrollTop: $("#Lay7aTextIn" + RecID).offset().top }, 500, 'swing');

        }
    });
}



//------- الاحكام الانجلوسكسونية المرتبطة
function showAngloRelated(id, recType) {

    $.ajax({
        type: "GET",
        url: "/Anglo/GetRelatedTits",
        data: { RecID: id, RecType: recType },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
        }
    });

}






//-------  اسأل سؤال بالسي شات
function AngloQAI(id, recType, Lang, OpenType) {
    var data =
    {
        var1: 6,
        var2: recType,
        var3: id,
        var4: Lang,
        var5: OpenType
    }
    var params = jQuery.param(data)

    var url = "/AI/Ask?" + params;
    window.open(url, '_blank');
} 

