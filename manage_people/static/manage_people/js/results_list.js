
$(document).ready(function(){

    var usersFound = $('.user-select-checkbox').length;

    if (usersFound){
        $('.users-found').removeClass('hidden');
        if ( usersFound == 1 ) {
            $('#add_users_form').find('select').removeClass('disabled');
            $('#user_create_button').removeClass('btn-disabled').addClass('btn-submit');
        }
        else if (usersFound > 1){
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        }
    } else {
        $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        $('.users-not-found').removeClass('hidden');
    }

    $('.user-select-checkbox').click(function(){
        toggleAlert();

        if( $('.user-select-checkbox:checked').size() > 0 ){
            if ($('#user_create_button').hasClass('btn-disabled')){
                $('#user_create_button').removeClass('btn-disabled').addClass('btn-submit');
            }
        }
        else {
            if ($('#user_create_button').hasClass('btn-submit')) {
                $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
            }
        }
    });

    $('#user_create_button').click(function(e){
        toggleAlert();
        $('#user_create_button').button('loading');

        var usersToAdd = {};
        $('.user-select-checkbox:checked').each(function(){
            usersToAdd[$(this).val()] = $(this).closest('li').find('select').val();
        });
        
        // Update hidden input element with users to add
        $('#add_users_form input[name="users_to_add"]').val(JSON.stringify(usersToAdd));
    });

    $('#form-show').click(function(e){
        //maintain the cancel link hidden
        $('#cancel_add_to_course').addClass('hidden');
        //hide the show btn
        $(this).addClass('hidden');
        //show the form with extra available IDs
        $('form').removeClass('hidden');
    });

    $('#form-hide').click(function(e){
        //hide the form
        $('form').addClass('hidden');
        //bring back the button to show the form
        $('#form-show').removeClass('hidden');
    });

    function toggleAlert(errorName, state, errorElements) {

        if (typeof errorName == 'undefined') {
            $('.alert-lti').toggleClass('hidden', true);
            $('.alert-lti li').toggleClass('hidden', true);
            $("#matching-records li").toggleClass('has-error', false);
        } else {
            var $alert = $('.alert-lti').toggleClass('hidden', state);
            $alert.find('li.' + errorName).toggleClass('hidden', state);
            $(errorElements).each(function(index, $el){
                $el.toggleClass('has-error', state);
            });
        }
    }
});
