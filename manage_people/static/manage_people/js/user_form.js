$(document).ready(function(){
    if (!$("#people-added li").length) {
        $('#no-users-added').removeClass('hidden');
    } else {
        $('#people-added').removeClass('hidden');
    }

    $('.deleteMenu').on('click', handleDeleteClick);

    function handleDeleteClick(e) {
        var $deleteBtn = $(this);
        var $userRow = $(this).closest('li');
        var sis_user_id = $userRow.attr('data-sisID');
        var canvas_role = $userRow.attr('data-role');
        var course_id = $('#canvas_course_id').text();
        var username = $userRow.find('.roster_user_name').text();
        e.preventDefault();
        var $modal = $('#confirm-remove-user').modal({keyboard: false});
        $modal.find('#confirm-remove-user-button').on('click', function () {
            var formData = {
                'canvas_course_id': course_id,
                'sis_user_id': sis_user_id,
                'canvas_role': canvas_role
            };
            $deleteBtn.off('click');
            $('#confirm-remove-user').modal('hide');
            $userRow.find('.fa-trash').removeClass('fa-trash').addClass('fa-spinner fa-spin');
            $.ajax({
                url: removeUserURL,
                type: "POST",
                data: formData,
                success: function (json) {
                    $userRow.fadeOut('slow', function () {
                        $('#user-removed-success').removeClass('hidden');
                        $userRow.remove();
                    });
                },
                error: function (xhr) {
                    $userRow.find('.fa-spinner').removeClass('fa-spinner fa-spin').addClass('fa-trash');
                    $deleteBtn.on('click', handleDeleteClick);
                    $('#user-removed-failed').removeClass('hidden');
                },
                complete: function () {
                    $('#confirm-remove-user-button').button('reset');
                    $('.server-response-alerts').addClass('hidden');
                    $('#err_username').html(username);
                    $('#success_username').html(username);
                }
            });
        });
        $modal.on('hide.bs.modal', function() {
            $modal.find('#confirm-remove-user-button').off('click');
        });
    }
});
