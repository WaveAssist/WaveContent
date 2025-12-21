import waveassist


# Initialize WaveAssist SDK (no check_credits flag in the starting node)
waveassist.init()


# Simple flat estimates for this assistant
CREDITS_NEEDED_FOR_RUN = 0.2
ESTIMATED_TIME_TO_PROCESS_SECONDS = 300


# Code starts here
print("WaveContent: Starting credits check and initialization...")

credits_needed_for_run = CREDITS_NEEDED_FOR_RUN
time_to_process = ESTIMATED_TIME_TO_PROCESS_SECONDS

success = waveassist.check_credits_and_notify(
    required_credits=credits_needed_for_run,
    assistant_name="WaveContent",
)



if not success:
    display_output = {
        "html_content": "<p>Credits were not available, the WaveContent run was skipped.</p>",
    }
    waveassist.store_data("display_output", display_output, run_based=True)
    raise Exception("Credits were not available, the WaveContent run was skipped.")
else:
    waveassist.store_data(
        "tentative_time_to_process",
        str(time_to_process),
        run_based=True,
    )
    waveassist.store_data(
        "credits_needed_for_run",
        credits_needed_for_run,
        run_based=True,
    )
    ##Convert competitor_websites to a list
    competitor_websites = waveassist.fetch_data("competitor_websites")
    if competitor_websites:
        competitor_websites = competitor_websites.split(",")
        competitor_websites = [website.strip() for website in competitor_websites]
        waveassist.store_data("competitor_websites_list", competitor_websites)
    else:
        waveassist.store_data("competitor_websites_list", [])
    
    ##Clean up website_url for Crawlee compatibility
    website_url = waveassist.fetch_data("website_url")
    if website_url:
        website_url = website_url.strip()
        # Convert http:// to https://
        if website_url.startswith("http://"):
            website_url = website_url.replace("http://", "https://", 1)
        # Add https:// if no protocol is present
        elif not website_url.startswith("https://"):
            website_url = f"https://{website_url}"
        waveassist.store_data("website_url", website_url)

print("WaveContent: Credits check complete and initialization finished.")

