import waveassist


# Initialize WaveAssist SDK (no check_credits flag in the starting node)
waveassist.init()


# Simple flat estimates for this assistant
CREDITS_NEEDED_FOR_RUN = 0.4
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
    waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
    raise Exception("Credits were not available, the WaveContent run was skipped.")
else:
    waveassist.store_data(
        "tentative_time_to_process",
        str(time_to_process),
        run_based=True,
        data_type="string",
    )
    waveassist.store_data(
        "credits_needed_for_run",
        str(credits_needed_for_run),
        run_based=True,
        data_type="string",
    )
    competitor_websites_raw = waveassist.fetch_data("competitor_websites", default="")
    competitor_websites = []
    if competitor_websites_raw and isinstance(competitor_websites_raw, str):
        competitor_websites = [w.strip() for w in competitor_websites_raw.split(",") if w.strip()]
    waveassist.store_data("competitor_websites_list", competitor_websites, data_type="json")

    website_url = waveassist.fetch_data("website_url", default="")
    if website_url and isinstance(website_url, str):
        website_url = website_url.strip()
        if website_url.startswith("http://"):
            website_url = website_url.replace("http://", "https://", 1)
        elif website_url and not website_url.startswith("https://"):
            website_url = f"https://{website_url}"
    if website_url:
        waveassist.store_data("website_url", website_url, data_type="string")

print("WaveContent: Credits check complete and initialization finished.")

