

//-------  التشريعات المرتبطة 
function showRelatedTash_AH(id, recType, lang) {
    var subTit = "التشريعات المرتبطة بـ :";
    if (lang == 2) { subTit = "Legislation related to: "; }
    var myType = 2;
    if (recType == 2) { myType = 3; }
    var data =
    {
        var0: myType,
        var1: recType,
        var2: id,
        var3: subTit + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: null,
        var5: lang
    }
    var params = jQuery.param(data)

    var url = "/referenced-legislation?" + params;
    window.open(url, '_blank');
}




function showRelatedETF_AH(id, recType, lang) {
    var subTit = "الإتفاقيات المرتبطة بـ : ";
    if (lang == 2) { subTit = "Agreements related to "; }

    var myType = 2;
    if (recType == 2) { myType = 3; }
    var data =
    {
        var0: myType,
        var1: recType,
        var2: id,
        var3: subTit + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: null,
        var5: lang
    }
    var params = jQuery.param(data)

    var url = "/related-treaties?" + params;
    window.open(url, '_blank');

}


//--------  المواد المرتبطة 
function showRelatedMada_AH(id, recType, lang) {
    $.ajax({
        type: "GET",
        url: "/Tash/AhkamRelatedTash",
        data: { RecID: id, RecType: recType, LangID: lang },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");

            $("#RelatedTashTable_"+ id+"_"+recType+">tbody>tr:first").trigger('click');
        }
    });
}



//--------  مواد الإتفاقيات المرتبطة  
function showRelatedETF_Mada_AH(id, recType, lang) {
    $.ajax({
        type: "GET",
        url: "/Etfakeat/AhkamRelatedEtef",
        data: { RecID: id, RecType: recType, LangID: lang },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");

            $("#RelatedTashTable_" + id + "_" + recType + ">tbody>tr:first").trigger('click');
        }
    });
}





//------ نصوص المواد التشريعية المرتبطة في نفس الشاشة   
function getRelatedTashMawaadListIn(RecID, RecType, TashID) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetAhkamRelatedMawaadByTashID",
        data: { RecID: RecID, RecType: RecType, TashID: TashID },
        success: function (ui) {
            $("#AhRelatedTashMawaadTextIn" + RecID + "_" + RecType).html(ui);
            $("#RelatedTashTable_" + RecID + "_" + RecType + "> tbody>tr").removeClass('tr_active');
            $("#RelatedTashB_" + RecID + "_" + RecType + "_" + TashID).addClass("tr_active");
        }
    });
}





//------- زر بيان النعي 
function showBayaanNa3y_AH(id, recType, lang) {
    $.ajax({
        type: "GET",
        url: "/Ahkam/GetFakraBayaanNa3y",
        data: { RecID: id, RecType: recType, LangID: lang },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
        }
    });
}

//-------  الدراسات المقارنة والاحكام المتعارضة والاحكام ذات الصلة 
function getAhkam2AhkamLink(id, recType, TableNo) {
    $.ajax({
        type: "GET",
        url: "/Ahkam/GetAhkam2AhkamLinkStep1",
        data: { RecID: id, RecType: recType, Table: TableNo },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
/*            if (ui.length > 1)*/
                $("#AhMokarnaDrasaatTable_" + id + ">tbody>tr:first").trigger('click');
/*            else getTitListIn(id, recType, TableNo, ui[0].id);*/

        }
    });
}




//------ الحصول على عناوين الدراسات المقارنة 
function getTitListIn(id, recType, TableNo, CntryID) {

    $("#AhMokarnaDrasaatTable_" + id + " tbody tr").removeClass('tr_active');
    $("#AhMokarnaDrasaat_" + id + "_" + CntryID).addClass("tr_active");

    $.ajax({
        type: "GET",
        url: "/Ahkam/GetAhkam2AhkamLinkStep2",
        data: { RecID: id, RecType: recType, Table: TableNo, CntryID: CntryID},
        success: function (result) {
            var html = "";
            for (var i = 0; i < result.length; i++) {
                html += "<tr id=\"AhMokarnaDrasaatTable2_Tr" + result[i].id + "_" + recType + "\" onclick =\"selectDrasaatTable2(" + id + ", " + result[i].id + ", " + recType + ")\" ondblclick =\"openAhkamDrasaatMokarna(" + result[i].id + ")\">"
                    + "<td class=\"data_table_design\">" + result[i].name + "</td></tr>"
            }
            $("#AhMokarnaDrasaatTable2_body_" + id + "_" + recType).html(html);
            $("#AhMokarnaDrasaatTable2_" + id + "_" + recType + ">tbody>tr:first").trigger('click');
        }
    });
}




//------- عند اختيار سجل من جدول الدراسات المقارنة  
function selectDrasaatTable2(tableID, recID, recType) {
    $("#AhMokarnaDrasaatTable2_" + tableID + "_" + recType +">tbody> tr").removeClass('tr_active');
    $("#AhMokarnaDrasaatTable2_Tr" + recID + "_" + recType).addClass("tr_active");

    $("#btn_AhMokarnaDrasaat_" + tableID + "_" + recType).removeAttr('onclick');
    $("#btn_AhMokarnaDrasaat_" + tableID + "_" + recType).attr('onClick', 'openAhkamDrasaatMokarna('+recID+');');
}



//------ استعراض الفقرات المرتبطة بالدراسات المقارنة 
function openAhkamDrasaatMokarna(id) {
    var data =
    {
        var0: 3,
        var1: 0,
        var2: id,
        var3: $("#AhMokarnaDrasaatTable2_Tr" + id).text(),
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents-paragraphs?" + params;
    window.open(url, '_blank');
}




//------ استعراض فقرات الأحكام المرتبطة بفهرس محدد
function openAhkamFehresRelated() {
    var data =
    {
        var0: 3,
        var1: 0,
        var2: $("#Tab2ID").val(),
        var3: $("#cntrySelect option:selected").text() + ' - ' + $("#courtsTypesSelect option:selected").text() + ' - ' + $("#Tab1Tit").val() + ' - ' + $("#Tab2Tit").val(),
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents-paragraphs?" + params;
    window.open(url, '_blank');
}




//------  اصتعراض الصور 
function showImage_AH(id,recType) {
    var data =
    {
      var1: 2,
      var2: recType,
      var3: id,
      var4: $("#subText_" + recType + "_" + id).html().substring(0, 250),
    }
    var params = jQuery.param(data) 

    var url = "/official-legal-images?" + params;
   window.open(url, '_blank');
}


//------  فتح شاشة النص الكامل للحكم   
function openFullText_AH(id, recType, Slug) {

    var colorText = $("#colorText_" + recType + "_" + id).html();

    var data =
    {
        type: recType,
        id: id
    }

    if (colorText !== '') {
        data.search = colorText;
    }

    var params = jQuery.param(data)

    var url = `/judgments-full-text/${Slug}?${params}`;
    window.open(url, '_blank');
}




//------  الإطلاع على النص الكامل للحكم   
function getFullText_AH(recType, id) {

    var _colorText = $("#colorText").html()
    $.ajax({
        type: "GET",
        url: "/Ahkam/GetFullText",
        data: { RecID: id, RecType: recType, colorText: _colorText },
        beforeSend: function () { $("body").addClass("loading"); },
        success: function (ui) {
            $("#FullText").html(ui);
            $("body").removeClass("loading");
        },
        error: function () { $("body").removeClass("loading"); }
    });
}




//------ اعقد مقارنة
function openFullText_Mokarna(ID1, ID2) {
    var data =
    {
        var1: ID1,
        var2: ID2
    }
    var params = jQuery.param(data)

    var url = "/judgment-comparison?" + params;
    window.open(url, '_blank');
}


//----- فتح النص الكامل لحكمين للمقارنة 
function getFullText_AH_Mokarna(ID1, ID2) {

    $.ajax({
        type: "GET",
        url: "/Ahkam/GetFullText",
        data: { RecID: ID1, RecType: 1, colorText: '', ShowSubMenu:false },
        beforeSend: function () { $("body").addClass("loading"); },
        success: function (ui) {
            $("#FullText1").html(ui);
            $("body").removeClass("loading");
        },
        error: function () { $("body").removeClass("loading"); }
    });

    $.ajax({
        type: "GET",
        url: "/Ahkam/GetFullText",
        data: { RecID: ID2, RecType: 1, colorText: '', ShowSubMenu: false },
        beforeSend: function () { $("body").addClass("loading"); },
        success: function (ui) {
            $("#FullText2").html(ui);
            $("body").removeClass("loading");
        },
        error: function () { $("body").removeClass("loading"); }
    });

}



//------- مسح واخفاء النص
function clearText_AH(id, recType) {
    $("#hidden_" + recType + "_" + id).html();
    $("#hidden_" + recType + "_" + id).addClass("hidden");
}





//------  فتح أحد الفهارس 
function goToAhMenuFehres(recID) {

    var data =
    {
        var1: recID,
        var2: 2,
        var3: $("#FehresLinkMenu_" + recID).text(),
        var4: recID
    }
    var params = jQuery.param(data)

    var url = "/legal-subjects?" + params;
    window.open(url, '_blank');

}



//------ تصفية نتائج الفهرس
function showFehresToSearch(recID) {

    var data =
    {
        var0: 3,
        var1: 0,
        var2: recID,
        var3: $("#FehresLinkMenu_" + recID).text()
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents-paragraphs?" + params;
    window.open(url, '_blank');

}





//-----  الوصول إلى فقرة محددة 
function goToAhFakraID(id) {

    $([document.documentElement, document.body]).animate({
        scrollTop: $("#subNoRep_" + id).offset().top
    }, 100);
}





//------   استعراض احاكم التتبع
//------   والاحكام المرتبطة   
function getLinkedAhkam(Id, recType, lang, e) {

    var resultType = 3;
    if (e == 2) { resultType = 4; }
    var data =
    {
        var0: resultType,
        var1: recType,
        var2: Id,
        var3: $("#subText_" + recType + "_" + Id).html().substring(0, 250),
        var5: lang,
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents?" + params;
    window.open(url, '_blank');
}



//--------   الفقرات المرتبطة بالحكم 
function getLinkedFakaraat(id, recType, lang) {

    var resultType = 8;
    if (recType == 2) { resultType = 9; }

    var data =
    {
        var0: resultType,
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var5: lang, 
    }

    var params = jQuery.param(data)

    var url = "/related-court-precedents-paragraphs?" + params;
    window.open(url, '_blank');
}



//------- تحليل الحكم 
function AnalyzeCase(id, Atype) {


    var data =
    {
        var1: Atype,
        var2: id,
    }
    var params = jQuery.param(data)

    var url = "/case-analysis?" + params;
    window.open(url, '_blank');
}


//-------  اسأل سؤال بالسي شات
function AhkamQAI(id, recType, Lang, OpenType) {
    var data =
    {
        var1: 2,
        var2: recType,
        var3: id,
        var4: Lang,
        var5: OpenType
    }
    var params = jQuery.param(data)

    var url = "/AI/Ask?" + params;
    window.open(url, '_blank');
} 