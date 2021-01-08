$('#btn-predict').click(function () {
    var form_data = new FormData($('#upload-file')[0]);

    $.ajax({
        type: 'POST',
        url: '/predict', //dung` window location
        data: form_data,
        contentType: false,
        cache: false,
        processData: false,
        async: true,
        success: function (response) {
                image_path = response['path'],
                bank = response['bank'],
                namecard = response['name'],
                type_card = response['type_card']
                valid_from = response['valid_from']
                good_thru = response['good_thru']
                number = response['number']

                console.log(image_path);
                console.log(bank);
                console.log(namecard);
                console.log(number);
                console.log(good_thru);

                drawImageOCR("/get_ori_img?imagepath="+image_path);
                loadLabel(image_path);
            },
    });

});

function drawImageOCR(src) {
    var canvas = document.getElementById("preview_img");
    IMGSRC = src;
    var context = canvas.getContext('2d');
    var imageObj = new Image();
    imageObj.onload = function() {
        canvas.width = this.width;
        canvas.height = this.height;
        context.drawImage(imageObj, 0, 0, this.width,this.height);
    };
    imageObj.src = src;
}

function loadLabel(image_path){
    $.ajax({
        url: 'get_label?imagepath='+image_path,
        type: 'get',
        dataType: 'json',
        contentType: 'application/json',  
        success: function (response) {
            if (response['code'] == 1001) {
                alert("[Lỗi] Không nhận được phản hồi từ server, vui lòng kiểm tra lại!");
            }
            if (response['code'] != 1201){
                console.log(response)
                bank = response['bank'],
                namecard = response['name'],
                date = response['date'],
                number = response['number'],
                pay = response['pay'],

                console.log("date: " + date);

                document.getElementById('bank').value = bank;
                document.getElementById('name').value = namecard;
                document.getElementById('date').value = date;
                document.getElementById('number').value = number;
                document.getElementById('pay').value = pay
            }
        }
    }).done(function() {
    
    }).fail(function() {
        alert('Fail!');
    });
}