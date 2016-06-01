$(document).ready(function(){

    var usersFound = $('#matching-records input[type="checkbox"]').length;
    if (usersFound){
        $('.users-found').removeClass('hidden');
        //make the dropdown enable if the the search only returns one result
        if ( usersFound == 1 ) {
            $('#add_users_form').find('select').removeClass('disabled');
        }
    } else {
        $('.users-not-found').removeClass('hidden');
    }
    

    $('#matching-records input[type="checkbox"]').click(function(){
        toggleAlert();
        //make dropdown available to use after the user checks the email
        var $select = $(this).closest('li').find('select');
        if ($(this).prop('checked')) {
            $select.removeClass('disabled');
            //if user checks an ID(checkbox) then the button becomes disabled and let the select menu choice make it available again
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        } else {
            $select.val($select.find('option:first').val());
            $select.addClass('disabled');
            //remove disabled class if the user 
            $('#user_create_button').removeClass('btn-disabled').addClass('btn-submit');
        }
        //if after checking/unchecking ids, set the submit button to disabled if all boxes are left unchecked
        checkChecked('add_users_form');
    });


    //clears out dropdown errors
    $('#matching-records select').change(function(){
        var hasCheck = $('#matching-records input:checked').length > 0;
        var rolesSelected = true;
        var missingRoleSelection = [];
        $('#matching-records input:checked').each(function(){
            var $li = $(this).closest('li');
            if ($li.find('select').val()==="choose") {
                rolesSelected = rolesSelected && false;
                missingRoleSelection.push($li);
                //if user hasn't picked a role then disable the button
                $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
            }

        });



        if (hasCheck && rolesSelected) {
            $('#user_create_button').removeClass('btn-disabled').addClass('btn-submit');
        }else{
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        }

        if ($(this).val() != $(this).find('option:first').val()) {
            
            toggleAlert();
            checkChecked('add_users_form');
        }

        //if the user resets the select menu to 'choose role' then disabled the button
        if ($(this).val() === "choose"){
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        }
    });

    $('#user_create_button').click(function(e){
       
        toggleAlert();
        $('#user_create_button').button('loading');

        var usersToAdd = {};
        $('#matching-records input:checked').each(function(){
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

    //looks for any selected checkboxes and any selected roles to enable/disable button
    function checkChecked(formname) {
        var anyBoxesChecked = false;
        var noRoleSelected = false;
        var $dd; 
        $('#' + formname + ' input[type="checkbox"]').each(function() {
            if ($(this).is(":checked")) {
                $dd = $(this).parent().find('select');
                anyBoxesChecked = true;
                //keeps a check for dropdowns without selection
                if ( $dd.val() == "choose" ){
                    noRoleSelected = true;
                }
            }
        });

        //if user had previously had chosen an email/HUID and role, but then chooses another id and no role while 
        //unchecking the first id with role then make sure to keep the button disabled
        if ( anyBoxesChecked && noRoleSelected ){
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        }else if (anyBoxesChecked == false) {
        //when all checkboxes are unchecked then keep the btn disabled
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        } 
    }

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
