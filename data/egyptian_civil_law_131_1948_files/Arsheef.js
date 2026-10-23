



// الحصول على جدول الارشيف
function getArsheefList() {
    var _myWhere = $("#ArsheefListSearch").val();
    $.ajax({
        type: "GET",
        url: "/Arsheef/GetArsheefList",
        data: { myWhere: _myWhere },
        success: function (result) {
            var html = "";
            for (var i = 0; i < result.length; i++) {
                html += "<tr id=myArcheefTable_" + result[i].id + " ondblclick=\"sendRecToArsheef()\"  onclick=\"selectArsheefRec(" + result[i].id + ")\" >"
                    + "<td  id=myArcheefTabletd_" + result[i].id + ">" + result[i].rowNum + "</td>"
                    + "<td   id=myArcheefTableName_" + result[i].id + " class=\"text-right\">" + result[i].name + "</td>"
                    + "<td>" + result[i].subCount + "</td></tr>";
            }
            $("#ArcheefTablebody").html(html);

            var recID = $("#ArcheefTableRecID_New").val();
            if (recID != '') selectArsheefRec(recID)
            else $("#myArcheefTable>tbody>tr:first").trigger('click');

            if ($("#ArcheefTablebody").html() != '') {
                $("#btn_ArsheefEdite").prop('disabled', false);
                $("#btn_ArsheefDelete").prop('disabled', false);
            }
            else {
                $("#btn_ArsheefEdite").prop('disabled', true);
                $("#btn_ArsheefDelete").prop('disabled', true);
            }
        }
    });
}





// مسح البحث في قائمة الارشيف 
function clearArsheefListSearch() {
    $("#ArsheefListSearch").val("");
    getArsheefList();
}




//- تحديد سجل في الارشيف 
function selectArsheefRec(e) {
    $('#myArcheefTable tbody tr').removeClass('tr_active');
    $("#myArcheefTable_" + e).addClass("tr_active");
    $("#ArcheefTableRecID").val(e);
}



//----  تنفيذ عملية الإضافة أو التعديل    
function arsheef_InsUpdate() {

    var myStatus = $('#Arsheef_InsUpStatus').val();

    if (myStatus == 1) addNewTitInArsheef();
    if (myStatus == 2) updateTitArsheef();

    if (myStatus == 3) addNewTitInIndexArsheef();
    if (myStatus == 4) updateTitIndexArsheef();
}



// اضافة عنوان جديد في الارشيف 
function prepare4ArsheefNew() {

    $('#Arsheef_InsUpStatus').val(1);
    $('#txtAddEditArcheefText').val('');
}

function addNewTitInArsheef() {
    var t = $('#txtAddEditArcheefText').val();
    $.ajax({
        type: "GET",
        url: "/Arsheef/AddNewTit",
        data: { Name: t },
        success: function (result) {
            $('#AddEditArcheefText').modal("toggle");
            $("#ArcheefTableRecID_New").val(result[0].id);
            getArsheefList();
        }
    });
}


//  تعديل العنوان المحدد  
function prepare4ArsheefUpdate() {

    $('#Arsheef_InsUpStatus').val(2);

    var id = $("#ArcheefTableRecID").val();
    var t = $('#myArcheefTableName_' + id).html();
    $('#txtAddEditArcheefText').val(t);
}

function updateTitArsheef() {
    var t = $('#txtAddEditArcheefText').val();
    var id = $("#ArcheefTableRecID").val();
    $.ajax({
        type: "GET",
        url: "/Arsheef/UpdateTit",
        data: { recID: id, Name: t },
        success: function (result) {
            $('#AddEditArcheefText').modal("toggle");
            $("#ArcheefTableRecID_New").val(result[0].id);
            getArsheefList();
        }
    });
}



//  حذف من قائمة الأرشيف 
function deleteFromArsheefList() {
    if (confirm('هل ترغب فعلا في حذف السجل الحالي ؟')) {
        var id = $("#ArcheefTableRecID").val();
        $.ajax({
            type: "GET",
            url: "/Arsheef/DeleteTit",
            data: { recID: id },
            success: function (result) {
                $("#ArcheefTableRecID_New").val(result[0].id);
                getArsheefList();
            }
        });
    }
}





// إضافة السجل إلى الأرشيف
function addInfoRecToArsheef() {
    var id = $("#ArcheefTableRecID").val();

    var info_RecId = $("#SendMeArsheef_ID").val();
    var recType    = $("#SendMeArsheef_RecType").val();
    var model      = $("#SendMeArsheef_Model").val();


    $.ajax({
        type: "GET",
        url: "/Arsheef/AddRecToArsheef",
        data: { recID: id, InfoRecID: info_RecId, InfoRecType: recType, InfoModel: model },
        success: function (result) {
            if (result[0].id == -1) { ShowMyMessage("السجل موجود في هذا الارشيف من قبل", "R") } else {

                ShowMyMessage("تمت إضافة السجل إلى الأرشيف بنجاح", "G");
            }
            $("#ArcheefTableRecID_New").val(id);
            getArsheefList();
        }
    });
}
