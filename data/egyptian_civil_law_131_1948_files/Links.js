
//-------  ترجمة المادة  
function enTranslate(id, recType) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetEnText",
        data: { RecID: id },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
        }
    });
}


//------  الأعمال التحضيرية 
function extraText(id, recType) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
    }
    var params = jQuery.param(data)

    var url = "/legislation-preparatory-works?" + params;
    window.open(url, '_blank');
}



//------   الأعمال التحضيرية في نفس الشاشة   
function extraTextIn(id, recType) {
    if (recType == 1) { extraText(id, recType) }
    else {
        $.ajax({
            type: "GET",
            url: "/Tash/GetExtraTextTitsIn",
            data: { RecID: id },
            success: function (ui) {
                $("#hidden_" + recType + "_" + id).html(ui);
                $("#hidden_" + recType + "_" + id).removeClass("hidden");
                $("#A3malTable_" + id + ">tbody>tr:first").trigger('click');
            }
        });
    }
}


//-------  الجرائم المرتبطة 
function showTashRelatedCrime(id, recType, lang) {
    $.ajax({
        type: "GET",
        url: "/Tash/Crime",
        data: { RecID: id, RecType: recType, Lang: lang },
        beforeSend: function () { $("body").addClass("loading"); },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
            $("body").removeClass("loading");
        },
        error: function () { $("body").removeClass("loading"); }
    });
}



//------  نصوص الأعمال التحضيرية   للعرض في نفس الشاشة 
function getExtraTextIn(RecID, A3malID) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetExtraText",
        data: { RecID: A3malID },
        success: function (result) {
            $("#A3malTextIn" + RecID).html(result[0].text);
            $("#A3malTable_" + RecID + "> tbody>tr").removeClass('tr_active');
            $("#A3malB_" + RecID + "_" + A3malID).addClass("tr_active");
        }
    });
}



//------ التطبيقات من الأحكام 
function showTashAhTat(id, recType, Year, Lang) {
    var subTit = "";
    if (Lang == 1) {
        if (recType == 1) subTit = "التطبيقات القضائية لنصوص مواد  "
        else subTit = "التطبيقات القضائية لنص المادة  ";
    } else {
        subTit = "Court Precedents: "
    }

    var data =
    {
        var0: 1,
        var1: recType,
        var2: id,
        var3: subTit + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: Year,
        var5: Lang,
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents-paragraphs?" + params;
    window.open(url, '_blank');
}



//------ التطبيقات من فتاوى مجلس الدولة 
function showTashFMGTat(id, recType, Year) {
    var subTit = "";
    if (recType == 1) subTit = "التطبيقات من الفتاوى الإدارية لنصوص مواد  "
    else subTit = "التطبيقات من الفتاوى الإدارية لنص المادة  ";
    var data =
    {
        var0: 1,
        var1: recType,
        var2: id,
        var3: subTit + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: Year,
    }
    var params = jQuery.param(data)

    var url = "/related-administrative-opinions?" + params;
    window.open(url, '_blank');
}






//------  استعلام الدستورية   
function showDostoria(id, recType, Lang, tit) {

    var data =
    {
        var0: 2,
        var1: recType,
        var2: id,
        var3: tit+ " : " + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: null,
        var5: Lang
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents?" + params;
    window.open(url, '_blank');
}



//------  المواد المقارنة    
function showMawaadMokarna(id, recType, Lang) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: Lang
    }
    var params = jQuery.param(data)

    var url = "/legislation-equivalent-articles?" + params;
    window.open(url, '_blank');
}



//-------   اعقد مقارنة مع النص المقابل 
function CompareWithCorrespondingArticle(id, recType, Lang) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: Lang
    }
    var params = jQuery.param(data)

    var url = "/legislation-compare-with-corresponding-article?" + params;
    window.open(url, '_blank');
}






//------  المواد المقارنة في نفس الشاشة   
function showMawaadMokarnaIn(id, recType, Lang) {
    if (recType == 1) { showMawaadMokarna(id, recType, Lang) }
    else {
        $.ajax({
            type: "GET",
            url: "/Tash/GetMokarnaCntryIn",
            data: { RecID: id, LangID: Lang },
            success: function (ui) {
                $("#hidden_" + recType + "_" + id).html(ui);
                $("#hidden_" + recType + "_" + id).removeClass("hidden");
                $("#CntryMMTable_" + id + ">tbody>tr:first").trigger('click');
            }
        });
    }
}





//------------ القضاء المقارن
function showTashKadaaMokaran(id, recType, Lang) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: Lang
    }
    var params = jQuery.param(data)

    var url = "/comparative-judiciary?" + params;
    window.open(url, '_blank');
}






//------------ القضاء المقارن في نفس الشاشة 
function showTashKadaaMokaranIn(id, recType, Lang) {
    if (recType == 1) { showTashKadaaMokaran(id, recType, Lang) }
    else {
        $.ajax({
            type: "GET",
            url: "/Tash/GetKadaaMokaranCntryIn",
            data: { RecID: id, LangID: Lang },
            success: function (ui) {
                $("#hidden_" + recType + "_" + id).html(ui);
                $("#hidden_" + recType + "_" + id).removeClass("hidden");
                $("#CntryKMTable_" + id + ">tbody>tr:first").trigger('click');
            }
        });
    }
}


//---------- استعراض حكم واحد من القضاء المقارن في نفس الشاشة
function getKadaaMokaranTopRecText(RecID, MadaID, CntryID, TatCount, MawaadIDs, CntryName, Lang) {

    var myCountText = "";

    $.ajax({
        type: "GET",
        url: "/Ahkam/GetFakraText",
        data: { RecType: 2, RecID: RecID, FehresDetailID: 0 },
        success: function (result) {

            // --- تعريف المتغيرات النصية بناءً على اللغة ---
            var textFound = "وجد إجمالي عدد ";
            var textRecord = " سجل - ";
            var textButton = "اضغط هنا لعرض الكل";

            if (Lang == 2) {
                textFound = "Total found ";
                textRecord = " record(s) - ";
                textButton = "Click here to view all";
            }

            if (TatCount > 1) {
                myCountText = textFound + TatCount + textRecord + "<input type=\"button\" class=\"btn_style1\" value=\"" + textButton + "\" onclick=\"showAllKadaaMokaran(" + MadaID + ",'" + MawaadIDs + "', '" + CntryName + "', '" + Lang + "')\">";
            }

            $("#KadaaMokaranTextIn" + MadaID).html(myCountText + "<br><br>" + result);
            $("#KadaaMokaranTextIn" + MadaID).scrollTop(0);
            $("#CntryKMTable_" + MadaID + " tbody tr").removeClass('tr_active');
            $("#CntryKM_" + MadaID + "_" + CntryID).addClass("tr_active");
        }
    });
}







//------ استعراض المزيد في القضاء المقارن 
function showAllKadaaMokaran(MadaID, Ids, CntryName, Lang) {
    var subTit = "التطبيقات القضائية المقارنة من دولة " + CntryName + " - ";
    if (Lang == 2) {
        subTit = "Comparative Judicial Applications from " + CntryName + " - ";
    }
    var data =
    {
        var0: 1,
        var1: 2,
        var2: Ids,
        var3: subTit + $("#subText_2_" + MadaID).html().substring(0, 250),
        var5: Lang
    }
    var params = jQuery.param(data)

    var url = "/related-court-precedents-paragraphs?" + params;
    window.open(url, '_blank');
}






//------  تتبع المادة في نفس الشاشة 
function showMawaadTatabo3In(id, recType, Lang) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetMawaadTatabo3",
        data: { RecID: id, LangID: Lang },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
        }
    });
}



//------  نصوص المواد المقارنة  للعرض في نفس الشاشة 
function getMokarnaListIn(RecID, CntryID) {    
    $.ajax({
        type: "GET",
        url: "/Tash/GetMokarnaList",
        data: { RecID: RecID, CntryID: CntryID },
        success: function (ui) {
            $("#MokarnaTextIn" + RecID).html(ui);
            $("#CntryMMTable_" + RecID +"> tbody>tr").removeClass('tr_active');
            $("#CntryMMB_" + RecID +"_"+ CntryID).addClass("tr_active");
        }
    });
}




//--------  اللائحة التنفيذية 
function showLay7a(id, recType, Lang) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: Lang,
    }
    var params = jQuery.param(data)

    var url = "/legislative-executive-regulation-1?" + params;
    window.open(url, '_blank');
}



//------    اللائحة التنفيذية في نفس الشاشة   
function showLay7aIn(id, recType, Lang) {
    if (recType == 1) { showLay7a(id, recType, Lang) }
    else {
        $.ajax({
            type: "GET",
            url: "/Tash/GetLay7aTashListIn",
            data: { RecID: id, Lang: Lang },
            success: function (ui) {
                $("#hidden_" + recType + "_" + id).html(ui);
                $("#hidden_" + recType + "_" + id).removeClass("hidden");
                $("#Lay7aTable_" + id + ">tbody>tr:first").trigger('click');
            }
        });
    }
}



//------  نصوص مواد اللائحة  في نفس الشاشة  
function getLay7aListIn(RecID, Lay7aID) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetLay7aListByTashID",
        data: { RecID: RecID, Lay7aID: Lay7aID },
        success: function (ui) {
            $("#Lay7aTextIn" + RecID).html(ui);
            $("#Lay7aTable_" + RecID + "> tbody>tr").removeClass('tr_active');
            $("#Lay7aB_" + RecID + "_" + Lay7aID).addClass("tr_active");

            $("#myText").animate({ scrollTop: $("#Lay7aTextIn" + RecID).offset().top }, 500, 'swing');
    
        }
    });
}



//--------  التشريعات المحال إليها في نفس الشاشة  
function getE7alaIn(id, recType, LangID) {
    if (recType == 1) { showE7ala(id, recType, LangID) }
    else {
        $.ajax({
            type: "GET",
            url: "/Tash/GetE7alaIn",
            data: { RecType: recType, RecID: id, LangID: LangID },
            success: function (ui) {
                $("#hidden_" + recType + "_" + id).html(ui);
                $("#hidden_" + recType + "_" + id).removeClass("hidden");
            }
        });
    }
}



//-------  تطبيقات التشريعات من الإتفاقيات   
function showTashEtefTat(id, recType) {

var myType = 4;
if (recType == 2) { myType = 5; }
var data =
{
    var0: myType,
    var1: recType,
    var2: id,
    var3: "الإتفاقيات المرتبطة بـ : " + $("#subText_" + recType + "_" + id).html().substring(0, 250),
    var4: null
}
var params = jQuery.param(data)

var url = "/related-treaties?" + params;
window.open(url, '_blank');

}





//-------- الإحالة في شاشة مستقلة   
function showE7ala(id, recType, LangID) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: LangID,
    }
    var params = jQuery.param(data)

    var url = "/legislation-referred-to?" + params;
    window.open(url, '_blank');
}




//--------  المواد المرتبطة 
function showMawaadLink(id, recType) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
    }
    var params = jQuery.param(data)

    var url = "/legislation-related-articles?" + params;
    window.open(url, '_blank');
}


//------  اصتعراض صور التشريعات
function showTashImage(id, recType, Lang) {
    var data =
    {
      var1: 1,
      var2: recType,
      var3: id,
      var4: $("#subText_" + recType + "_" + id).val().substring(0, 250),
      var5: Lang
    }
    var params = jQuery.param(data) 

    var url = "/official-legal-images?" + params;
   window.open(url, '_blank');
}


//------ فتح شاشة تبويبات التشريع 
function showTashFehres(id, recType, Lang) {
    var data =
    {
      var1: recType,
      var2: id,
      var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
      var4: Lang
    }
    var params = jQuery.param(data) 
    var url = "/legislation-index?" + params;
    window.open(url, '_blank');
} 




//-----------------------------------------------------------------------------------------

//------  مواد التشريع  
function showTashMawaad(id, recType, Lang) {
    var rawText = $("#subText_" + recType + "_" + id).html().substring(0, 250);
    var cleanText = rawText.trim() ? encodeURIComponent(rawText) : "eastlaws.com";
    var url = "/legislation-articles/" + recType + "/" + id + "/" + cleanText + "/" + Lang;
    window.open(url, '_blank');
}



//-------  اسأل سؤال بالسي شات
function TashQAI(id, recType, Lang, OpenType) {
    var data =
    {
        var1: 1,
        var2: recType,
        var3: id,
        var4: Lang,
        var5: OpenType
    }
    var params = jQuery.param(data)

    var url = "/AI/Ask?" + params;
    window.open(url, '_blank');
} 








//-------- النص الكامل للتشريع 
function openTashFullText(id, recType, madaID, Slug) {    

    var colorText = $("#colorText_" + recType + "_" + id).html();
    var madaID = madaID || "0";

    var data =
    {
        type: recType,
        id: id,
        sub: madaID,
    }

    if (colorText !== '') {
        data.search = colorText;
    }

    var params = jQuery.param(data)

    var url = `/legislation-full-text/${Slug}?${params}`;
    window.open(url, '_blank');
}





//-------- فتح تشريع والوصول إلى المادة  
function openFullTextGoToMada(id, recType, MadaID, Slug) {
    var data =
    {
        type: recType,
        id: id,
        sub: MadaID
    }
    var params = jQuery.param(data)

    var url = `/legislation-full-text/${Slug}?${params}`;
    window.open(url, '_blank');
}




//--------------------------------------------------------------------------------------
//------   التعديلات   
//------   السريان
function showTa3deel(e, id, recType, LangID) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: e,
        var4: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var5: LangID,
    }
    var params = jQuery.param(data) 
    var url = "/legislation-Legislation Updates?" + params;
    window.open(url, '_blank');
} 


//------  العلاقات السابقة 
function showOldRelation(id, recType, LangID) {
    var data =
    {
        var1: recType,
        var2: id,
        var3: $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: LangID,
    }
    var params = jQuery.param(data)
    var url = "/legislation-history?" + params;
    window.open(url, '_blank');
} 


//-------  التعديلات في نفس الشاشة
function showTa3deelIn(e, id, recType, langID) {

    if (recType == 1) { showTa3deel(e, id, recType, langID) }
    else {
        $.ajax({
            type: "GET",
            url: "/Tash/GetT3delaatListIn",
            data: { var1: recType, var2: id, var3: e, var4:langID },
            success: function (ui) {
                $("#hidden_" + recType + "_" + id).html(ui);
                $("#hidden_" + recType + "_" + id).removeClass("hidden");
                $("#EffectTable_" + id + ">tbody>tr:first").trigger('click');
            }
        });
    }
}



//------  نصوص مواد التعديلات في نفس الشاشة   
function getTa3deelTextIn(RecID, MadaID, Ta3deelID) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetMadaText",
        data: { RecID: MadaID, FehresDetailID: 0 },
        success: function (ui) {
            $("#EffectTextIn" + RecID).html(ui);
            $("#EffectTable_" + RecID + "> tbody>tr").removeClass('tr_active');
            $("#EffectB_" + RecID + "_" + Ta3deelID).addClass("tr_active");
        }
    });
}



//------ التطور التشريعي للمادة   
function showMadaHistory(id, recType, LangID) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetMawaadHistory",
        data: { RecType: recType, RecID: id, LangID: LangID },
        success: function (ui) {
            $("#hidden_" + recType + "_" + id).html(ui);
            $("#hidden_" + recType + "_" + id).removeClass("hidden");
        }
    });
}



//------- مسح واخفاء النص
function clearText(id, recType) {
    $("#hidden_" + recType + "_" + id).html();
    $("#hidden_" + recType + "_" + id).addClass("hidden");
}


//------  الإطلاع على النص الكامل
function openFullText_QJ(id) {
    var data =
    {
        var1: id,
        var2: $("#colorText_" + id).html()
    }
    var params = jQuery.param(data)

    var url = "/qatar-irl-full-text?" + params;
    window.open(url, '_blank');
}


//------- الاحكام الانجلوسكسونية المرتبطة
function showTashAngloSakTatMaster(id, recType, subType) {

    var subTit = "Related Court Precedents : ";
    if (subType == 2) {
        subTit = "Conflict of Jurisdiction : ";
    }

    var data =
    {
        var0: recType,
        var1: recType,
        var2: id,
        var3: subTit + $("#subText_" + recType + "_" + id).html().substring(0, 250),
        var4: subType
    }
    var params = jQuery.param(data)

    var url = "/judgements-anglosaxon-search?" + params;
    window.open(url, '_blank');
}



//------- تحليل المادة
function AnalyzeArticle(id, recType) {

    if (recType !== 2) {
        return; 
    }

    var data =
    {
        var1: 1,
        var2: id,
    }
    var params = jQuery.param(data)

    var url = "/case-analysis?" + params;
    window.open(url, '_blank');
}