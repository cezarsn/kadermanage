#!/usr/bin/env python3

"""
Features to add:
Move one months further before months end.
https://ffm-shaolin-kulturzentrum.kadermanager.de/calendar/monthly?date=2020-11-01

"""

import yaml
import os
import mechanicalsoup
import datetime
import pprint


class LoadFile:
    def __init__(self, path_name=".", file_name="credentials.yaml"):
        self.path_name = path_name
        self.file_name = file_name

    def load_data(self):
        file_path = os.path.join(self.path_name, self.file_name)
        if os.path.exists(file_path):
            with open(file_path) as file:
                document = yaml.full_load(file)
            return document
        else:
            return False

YEAR = datetime.datetime.today().year

def get_month(time):
    """
    https://ffm-shaolin-kulturzentrum.kadermanager.de/calendar/monthly?date=2020-11-01
    """
    dt = datetime.datetime.today()
    if time == "current":
        dt = dt.replace(day=1)
    if time == "next":
        dt = dt.replace(month=dt.month + 1, day=1)
    return f"{dt.strftime('%Y-%m-%d')}"


class BrowsePage:
    def __init__(self, url):
        self.url = url
        self.browser = mechanicalsoup.StatefulBrowser()
        self.player_id = ""

    def login(self, user_name, password):
        self.browser.open(self.url)
        self.browser.get_current_page()
        self.browser.select_form()
        # print form inputs
        # browser.get_current_form().print_summary()
        # specify username and password
        self.browser["login_name"] = user_name
        self.browser["password"] = password

        # submit form
        self.browser.submit_selected()
        response_after_login = self.browser.get_current_page()

        meta_elem = response_after_login.find("meta", {"name": "player-id"})
        self.player_id = meta_elem.attrs["content"]

    def get_monthly_calendar(self, course_name, month):
        '''
        function to parse the mont page and collect the enrollment url's
        :return: a dictionary of links

        This is how and element looks like:

        <a href="https://ffm-shaolin-kulturzentrum.kadermanager.de/events/14346476" target="_top">
        <div class="event event_type_3 light hover bootstrap-tooltip  ">
          <span class="time">19:00</span>
          <span class="info">Tai Chi + Qi Gong I</span>
          <span title="" class="place tooltip-bootstrap" data-original-title="Frankfurt Shaolin Kulturzentrum Shaolin Kung-Fu, Wilhelm-Gutbrod-Straße 19,  60437 Frankfurt am Main"><i class="icon icon-map-marker"></i></span>
          <span class="event-enrollments-icons">
            <span class="tooltip-bootstrap" title="" data-placement="bottom" data-original-title="Zusagen: (Niemand)">
                <i class="icon icon-thumbs-up icon"></i>
                <span>In</span>
            0</span>
            <span class="tooltip-bootstrap" title="" data-placement="bottom" data-original-title="Absagen: Polina, Uwe S">
                <i class="icon icon-thumbs-down icon"></i><span>Out</span>
            2</span>
        </span>
        </div>
        </a>
        '''

        link_collection = {}
        event_time = ""
        event_title = ""
        event_participants_absagen = ""
        event_participants_zusagen = ""

        self.browser.open(f"{self.url}/calendar/monthly?date={month}")
        response_monthly = self.browser.get_current_page()
        for elem in response_monthly.find_all("a", href=True):
            if elem and course_name in elem.text:
                event_url = elem.attrs["href"]
                for chldrn in elem.descendants:
                    if chldrn.name == "span" and chldrn.has_attr("class"):
                        if chldrn["class"][0] == "time":
                            event_time = chldrn.text
                        if chldrn["class"][0] == "info":
                            event_title = chldrn.text
                        if chldrn["class"][0] == "tooltip-bootstrap":
                            if "Absagen" in chldrn["title"]:
                                event_participants_absagen = chldrn["title"]
                            if "Zusagen" in chldrn["title"]:
                                event_participants_zusagen = chldrn["title"]

            if event_time and event_title and event_participants_absagen and event_participants_zusagen:
                link_collection[event_url] = [event_time, event_title,
                                              event_participants_absagen,
                                              event_participants_zusagen]
        return link_collection

    def get_event(self, event_url):
        enroll_url = f"{event_url}"
        self.browser.open(enroll_url)
        enroll_page = self.browser.get_current_page()
        enrollment_date = enroll_page.title.text.split(",")[1]
        date = enrollment_date.strip().split(" ")[1]
        time = enrollment_date.strip().split(" ")[-1]
        dateandtime = f"{date}{YEAR} {time}"
        enroll_date = datetime.datetime.strptime(dateandtime, "%d.%m.%Y %H:%M")

        print(f"[*] Info: accessing the event from - {enroll_date}")
        return enroll_date

    def enroll_event(self, event_url):
        enroll_url = f"{event_url}/enroll?" \
                     f"enroll=1&" \
                     f"enroll_type=events_own&" \
                     f"enroll_type_ga_addon=&" \
                     f"player_id={self.player_id}"
        self.browser.open(enroll_url)

    def unroll_event(self, event_url):
        unroll_url = f"{event_url}/enroll?" \
                     f"enroll=2&" \
                     f"enroll_type=events_own&" \
                     f"enroll_type_ga_addon=&" \
                     f"player_id={self.player_id}"
        self.browser.open(unroll_url)

        print(f"[*] Debug: unroll URL - {unroll_url}")


def main():
    link_collection = {}
    document = LoadFile('.', 'credential.yml').load_data()
    user_name, password, team_name, course_name = document['user_name'], \
                                                  document['password'], \
                                                  document['team_name'], \
                                                  document['course_name']

    print(f"[*] Debug loading credentials: {user_name} {password} {team_name}")
    url = f"https://{team_name}.kadermanager.de"

    browser = BrowsePage(url=url)
    browser.login(user_name=user_name, password=password)
    this_month = get_month("current")
    link_collection.update(browser.get_monthly_calendar(course_name, this_month))
    if datetime.datetime.today().day > 20:
        next_month = get_month("next")
        link_collection.update(browser.get_monthly_calendar(course_name, next_month))

    # enroll if you are not part of already enrolled uses
    for link in link_collection.keys():
        if "Cezar" not in link_collection[link][-1]:
            dateandtime = browser.get_event(link)
            if dateandtime.weekday() != 5:
                print(f"[*] Info: Enrolling the user day for {dateandtime.weekday()}- {dateandtime}")
                browser.enroll_event(link)
            time_interval = (datetime.datetime.today() - dateandtime)
            time_interval_sec = time_interval.seconds//3600
            time_interval_days = time_interval.days
            if dateandtime.weekday() == 5 and time_interval_sec < 20 and time_interval_days == 0:
                print(f"[*] Info: Enrolling the user day for {dateandtime.weekday()}- {dateandtime}")
                browser.enroll_event(link)


if __name__ == "__main__":
    main()
