document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("searchInput");
    const typeFilter = document.getElementById("typeFilter");
    const maxRent = document.getElementById("maxRent");
    const availableOnly = document.getElementById("availableOnly");

    const hostelItems = document.querySelectorAll(".hostel-item");

    const noResults = document.getElementById("noResults");
    const resultCount = document.getElementById("resultCount");


    function filterHostels() {

        const searchText = searchInput
            ? searchInput.value.toLowerCase().trim()
            : "";

        const selectedType = typeFilter
            ? typeFilter.value
            : "";

        const maximumRent = maxRent && maxRent.value
            ? parseFloat(maxRent.value)
            : Infinity;

        const onlyAvailable = availableOnly
            ? availableOnly.checked
            : false;


        let visibleCount = 0;


        hostelItems.forEach(function (item) {

            const name = item.dataset.name || "";
            const area = item.dataset.area || "";
            const city = item.dataset.city || "";
            const type = item.dataset.type || "";

            const rent = parseFloat(item.dataset.rent) || 0;
            const available = parseInt(item.dataset.available) || 0;


            // Search condition

            const matchesSearch =
                name.includes(searchText) ||
                area.includes(searchText) ||
                city.includes(searchText);


            // Hostel type condition

            const matchesType =
                selectedType === "" ||
                type === selectedType;


            // Rent condition

            const matchesRent =
                rent <= maximumRent;


            // Vacancy condition

            const matchesAvailability =
                !onlyAvailable ||
                available > 0;


            // Final result

            if (
                matchesSearch &&
                matchesType &&
                matchesRent &&
                matchesAvailability
            ) {

                item.style.display = "";

                visibleCount++;

            } else {

                item.style.display = "none";

            }

        });


        // Update result count

        if (resultCount) {

            resultCount.textContent =
                visibleCount + " Hostels";

        }


        // Show / hide no results message

        if (noResults) {

            if (visibleCount === 0) {

                noResults.style.display = "block";

            } else {

                noResults.style.display = "none";

            }

        }

    }


    // Search box

    if (searchInput) {

        searchInput.addEventListener(
            "input",
            filterHostels
        );

    }


    // Hostel type

    if (typeFilter) {

        typeFilter.addEventListener(
            "change",
            filterHostels
        );

    }


    // Maximum rent

    if (maxRent) {

        maxRent.addEventListener(
            "input",
            filterHostels
        );

    }


    // Vacancy only

    if (availableOnly) {

        availableOnly.addEventListener(
            "change",
            filterHostels
        );

    }


    // Run once when page loads

    filterHostels();

});