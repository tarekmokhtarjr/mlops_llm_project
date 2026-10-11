


//------ اظهار الرسائل 
function ShowMyMessage(S, T) {

    var alertType = "";

    if (T == "G") alertType = "alert-success";
    if (T == "B") alertType = "alert-info";
    if (T == "R") alertType = "alert-danger";

    $("#" + alertType).html(S);
    $("#" + alertType).removeClass('alert_hide');
    $("#alerts_messages").removeClass('alert_hide');
    setTimeout(function () {
        $("#" + alertType).addClass('alert_hide');
        $("#alerts_messages").addClass('alert_hide');
    }, 1000);
}



//-------  مسح خانة البحث 
function clearInputText(e) {
    $('input[name=' + e + ']').val("");
}



//-------  الإملاء الصوتي
function voiceInputText(e) {
    var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'ar-SA'; // Set language to Arabic (Saudi Arabia)
    recognition.start();

    recognition.onresult = function (event) {
        var transcript = event.results[0][0].transcript;
        $('input[name=' + e + ']').val(transcript);
    };

    recognition.onerror = function (event) {
        console.error('خطأ في التعرف على الصوت:', event.error);
    };
}
