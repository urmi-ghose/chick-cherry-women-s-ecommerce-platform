// some scripts

// jquery ready start
$(document).ready(function () {
  console.log("script.js loaded and ready");
  // jQuery code

  /* ///////////////////////////////////////

    THESE FOLLOWING SCRIPTS ONLY FOR BASIC USAGE,
    For sliders, interactions and other

    */ ///////////////////////////////////////

  //////////////////////// Prevent closing from click inside dropdown
  $(document).on("click", ".dropdown-menu", function (e) {
    e.stopPropagation();
  });

  $(".js-check :radio").change(function () {
    var check_attr_name = $(this).attr("name");
    if ($(this).is(":checked")) {
      $("input[name=" + check_attr_name + "]")
        .closest(".js-check")
        .removeClass("active");
      $(this).closest(".js-check").addClass("active");
      // item.find('.radio').find('span').text('Add');
    } else {
      item.removeClass("active");
      // item.find('.radio').find('span').text('Unselect');
    }
  });

  $(".js-check :checkbox").change(function () {
    var check_attr_name = $(this).attr("name");
    if ($(this).is(":checked")) {
      $(this).closest(".js-check").addClass("active");
      // item.find('.radio').find('span').text('Add');
    } else {
      $(this).closest(".js-check").removeClass("active");
      // item.find('.radio').find('span').text('Unselect');
    }
  });

  //////////////////////// Bootstrap tooltip
  if ($('[data-toggle="tooltip"]').length > 0) {
    // check if element exists
    $('[data-toggle="tooltip"]').tooltip();
  } // end if

  function showNotification(message, type) {
    var notification = $(
      '<div class="notification ' + type + '">' + message + "</div>"
    );
    $("body").append(notification);
    notification
      .fadeIn()
      .delay(3000)
      .fadeOut(function () {
        $(this).remove();
      });
  }

  // Handle remove cart item form submission with AJAX
  $(document).on('submit', '.remove-form', function(e) {
    e.preventDefault();
    var form = $(this);
    var url = form.attr('action');
    var formData = form.serialize();

    $.ajax({
      type: 'POST',
      url: url,
      data: formData,
      success: function(response) {
        if (response.success) {
          // Update cart count in navbar if exists
          if (response.cart_count !== undefined) {
            $('.cart-count').text(response.cart_count);
          }
          // Reload the page to update cart
          location.reload();
        } else {
          showNotification('Error removing item from cart', 'error');
        }
      },
      error: function() {
        showNotification('Error removing item from cart', 'error');
      }
    });
  });

});
// jquery end
