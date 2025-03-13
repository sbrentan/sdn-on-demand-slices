// Open modal function accepting a callback
function openServicesModal(callback) {
	// Reset form fields
	$('#addServiceForm')[0].reset();
	$('#portsContainer').empty();
	$('#servicesModal').modal('show');
	
	// Set up save button click
	$('#saveServiceBtn').off('click').on('click', function() {
		// Construct IP from the four inputs
		var ip = $('#ip1').val() + '.' + $('#ip2').val() + '.' + $('#ip3').val() + '.' + $('#ip4').val();

		// Gather ports from the pill badges
		var ports = [];
		$('#portsContainer .port-pill').each(function() {
			var portText = $(this).clone().children().remove().end().text().trim();
			if (portText) {
				ports.push(portText);
			}
		});
		
		$('#servicesModal').modal('hide');
		if (callback && typeof callback === 'function') {
			callback(ip, ports);
		}
	});
}


document.addEventListener('DOMContentLoaded', function() {
	// IP input: remove non-digit characters
	$('.ip-segment').on('input', function() {
		this.value = this.value.replace(/[^0-9]/g, '');
		// IP input: Clamp value between 0 and 255 on blur
		var val = parseInt($(this).val(), 10);
		if (isNaN(val)) {
			$(this).val('');
			return;
		}
		if (val > 255) {
			$(this).val(255);
		} else if (val < 0) {
			$(this).val(0);
		} else {
			$(this).val(val); // Removes any leading zeros
		}
	});

	// IP input: when dot is pressed, move to next field
	$('.ip-segment').on('keydown', function(e) {
		if (e.key === '.') {
			e.preventDefault();
			var nextInput = $(this).nextAll('.ip-segment').first();
			if (nextInput.length) {
				nextInput.focus();
			}
		}
	});

	// Port addition logic
	$('#addPortBtn').on('click', function() {
		$('#addPortBtn').hide();
		var portInput = $('<input type="number" step="1" class="form-control port-input" placeholder="Enter port">');
		portInput.insertAfter('#portsContainer').focus();
		
		// When the user presses Enter, trigger the blur event to add the port
		portInput.on('keydown', function(e) {
			if (e.key === 'Enter') {
				e.preventDefault();
				$(this).blur();
			} else if (e.key === 'Escape') {
				e.preventDefault();
				e.stopPropagation();
				$(this).remove();
				$('#addPortBtn').show();
			} else if (e.key === '.') {
				e.preventDefault();
			}
		});

		// On blur, add the entered port as a pill (if a valid integer)
		portInput.on('blur', function() {
			var rawVal = $(this).val();
			var portVal = parseInt(rawVal, 10);
			if (!isNaN(portVal)) {
				var pill = $('<span class="badge badge-pill badge-secondary port-pill">' + 
							  portVal + ' <a href="#" class="text-white ml-1 remove-port">&times;</a></span>');
				$('#portsContainer').append(pill);
			}
			$(this).remove();
			$('#addPortBtn').show();
		});
	});

	// Delegate click event for removing a port pill
	$('#portsContainer').on('click', '.remove-port', function(e) {
		e.preventDefault();
		$(this).parent('.port-pill').remove();
	});
});
