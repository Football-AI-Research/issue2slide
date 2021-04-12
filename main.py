from __future__ import print_function

import os
import os.path
import pickle
from datetime import date

import mistune
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fire import Fire
from github import Github
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icecream import ic
from rich import inspect, print

load_dotenv()
ENV = os.environ

HEADER_2_ATTRIBUTES = {
    "1. overview (basic ideas)": "overview",
    "2. novelty": "novelty",
    "3. method (technical details)": "method",
    "4. results": "results",
    "5. links to papers, codes, etc.": "links",
    "6. thoughts, comments": "thoughts",
    "7. bibtex": "bibtex",
    "8. related papers": "related_papers",
}


class SlidesApi:
    def __init__(self, PRESENTATION_ID):
        self.presentation_id = PRESENTATION_ID
        self.service = self.launch_api()
        self.read_slides()
        self.get_elements()

    @property
    def df(self):
        return pd.DataFrame(self.page_element_list)

    def launch_api(self):
        SCOPES = ["https://www.googleapis.com/auth/presentations"]

        creds = None
        if os.path.exists("slede_token.pickle"):
            with open("slede_token.pickle", "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("slede_token.pickle", "wb") as token:
                pickle.dump(creds, token)

        service = build("slides", "v1", credentials=creds)

        return service

    def read_slides(self):
        presentation = (
            self.service.presentations()
            .get(presentationId=self.presentation_id)
            .execute()
        )
        self.slides = presentation.get("slides")

    def get_elements(self):
        self.read_slides()
        self.page_element_list = []

        for page_num in range(0, len(self.slides), 1):
            for element in self.slides[page_num]["pageElements"]:
                if "shape" in list(element.keys()):
                    self.page_element_list.append(
                        {
                            "page": page_num,
                            "type": element["shape"]["placeholder"]["type"],
                            "objectId": element["objectId"],
                            "contents": extract_text_from_shape(element["shape"]),
                        }
                    )

                elif "table" in list(element.keys()):
                    self.page_element_list.append(
                        {
                            "page": page_num,
                            "type": "TABLE",
                            "objectId": element["objectId"],
                            "contents": extract_text_from_table(element["table"]),
                        }
                    )

        return self.page_element_list

    def find_shape_by_page(self, find_type, find_page):
        self.result_shape = []

        for lst in self.page_element_list:
            if (lst["page"] == find_page) and (lst["type"] == find_type):
                self.result_shape.append(lst)

        return self.result_shape

    def get_shape(self, find_type, find_page=None, find_title=None):
        self.result_shape = []

        if find_page is not None:
            self.result_shape = self.find_shape_by_page(find_type, find_page)

        elif find_title is not None:
            page_num = None

            for lst in self.page_element_list:
                if (find_title in lst["contents"][0]) and (lst["type"] == find_type):
                    page_num = lst["page"]

            if page_num is not None:
                self.result_shape = self.find_shape_by_page(find_type, page_num)

        return self.result_shape

    def clear_shape_contents(self, objectId):
        requests = []

        requests.append(
            {
                "deleteText": {
                    "objectId": objectId,
                    "textRange": {
                        "type": "ALL",
                    },
                }
            }
        )

        try:
            body = {"requests": requests}
            response = (
                self.service.presentations()
                .batchUpdate(presentationId=self.presentation_id, body=body)
                .execute()
            )
            self.read_slides()
            self.get_elements()
            print("Result: Clear the contents successfully")
        except:
            print("Exception: Failed to clear contents in the table ")

    def remove_slide(self, pageId):
        requests = []

        requests.append(
            {
                "deleteObject": {
                    "objectId": pageId,
                }
            }
        )

        try:
            body = {"requests": requests}
            response = (
                self.service.presentations()
                .batchUpdate(presentationId=self.presentation_id, body=body)
                .execute()
            )
            self.read_slides()
            self.get_elements()
            print("Result: removed the slide successfully")
        except Exception as e:
            print("Exception: Failed to remove the slide ")
            print(e)

    def add_slide(
        self, layoutID=None, predefinedLayoutID=None, pageId=None, insertionIndex="0"
    ):
        requests = []

        request = {
            "createSlide": {
                "insertionIndex": insertionIndex,
            }
        }

        if pageId:
            request["createSlide"]["objectId"] = pageId
        if layoutID:
            request["createSlide"]["slideLayoutReference"] = {"layoutId": layoutID}
        elif predefinedLayoutID:
            request["createSlide"]["slideLayoutReference"] = {
                "predefinedLayout": predefinedLayoutID
            }
        requests.append(request)
        try:
            body = {"requests": requests}
            response = (
                self.service.presentations()
                .batchUpdate(presentationId=self.presentation_id, body=body)
                .execute()
            )

            self.read_slides()
            self.get_elements()
            pageId = response["replies"][0]["createSlide"]["objectId"]
            print("Result: Added to add slide successfully")
            return pageId
        except Exception as e:
            print("Exception: Failed to add slide")
            print(e)

    def writes_text_to_shape(self, objectId, text, default_index=0):
        requests = []

        requests.append(
            {
                "insertText": {
                    "objectId": objectId,
                    "text": text,
                    "insertionIndex": default_index,
                }
            }
        )
        try:
            body = {"requests": requests}
            response = (
                self.service.presentations()
                .batchUpdate(presentationId=self.presentation_id, body=body)
                .execute()
            )
            self.read_slides()
            self.get_elements()
        except:
            print("Exception: Failed to add contents to the table ")


def extract_text_from_shape(element_dict):

    text_box = []
    if "text" not in list(element_dict.keys()):
        pass
    else:
        element_dict["text"]["textElements"]
        for lst in element_dict["text"]["textElements"]:
            if "textRun" in list(lst.keys()):
                text_box.append(lst["textRun"]["content"])

    return text_box


class Slide:
    def __init__(self):
        self.title = None
        self.subtitle = None
        self.authors = None
        self.overview = None
        self.novelty = None
        self.method = None
        self.results = None
        self.links = None
        self.comments = None
        self.bibtex = None
        self.related_papers = None

    def from_issue(self, issue):
        self.title = issue.title
        self.labels = [label.name for label in issue.labels]
        self.issue_url = issue.html_url

        # Break down body
        soup = BeautifulSoup(mistune.html(issue.body), "lxml")
        headers = soup.find_all("h2")
        for header in headers:
            attribute = HEADER_2_ATTRIBUTES[header.text.lower()]
            text = []

            for sib in header.find_next_siblings():
                if sib.name == "h2":
                    break
                else:
                    text += sib.text
            text = "".join(text)
            setattr(self, attribute, text)
        return self


def main():

    # init github client
    g = Github(ENV["GITHUB_ACCESS_TOKEN"])

    # Get all github issues in survey repos assigned to me
    repo_names = ["ComputerVisionLaboratory/survey"]
    issues = []

    for repo_name in repo_names:
        repo = g.get_repo(repo_name)
        issues += repo.get_issues(assignee="atomscott")

    slides = SlidesApi("1IO6kAIiIUu13C7ezA8-nA9Nv7yBwJyOG1uj3HXv8xGA")

    # Remove all existing slides
    for slide in slides.slides:
        slides.remove_slide(slide["objectId"])

    # Convert issues to padas dataframe
    for issue in issues:

        # Add individual slides
        pageId = slides.add_slide(layoutID="gced22f2579_0_11")[:-2]
        page_df = slides.df[slides.df.objectId.str.startswith(ic(pageId))]

        # Create slide from issue information
        slide = Slide().from_issue(issue)

        # Add title and subtitle information
        title_obj_id = ic(page_df)[page_df.type == "TITLE"].objectId.values[0]
        subtitle_obj_id = page_df[page_df.type == "SUBTITLE"].objectId.values[0]
        slides.writes_text_to_shape(objectId=title_obj_id, text=slide.title)
        slides.writes_text_to_shape(objectId=subtitle_obj_id, text=slide.subtitle)

        for idx, object_id in enumerate(
            sorted(page_df.objectId[page_df.type == "BODY"])
        ):
            try:
                text = getattr(slide, list(HEADER_2_ATTRIBUTES.values())[idx])
                slides.writes_text_to_shape(objectId=object_id, text=text)
            except Exception as e:
                ic(e)

    # Add Title Slide
    title_id = slides.add_slide(predefinedLayoutID="TITLE")[:-2]
    title_df = slides.df[ic(slides.df.objectId).str.startswith(ic(title_id), na=False)]

    title_obj_id = ic(title_df)[title_df.type == "CENTERED_TITLE"].objectId.values[0]
    subtitle_obj_id = title_df[title_df.type == "SUBTITLE"].objectId.values[0]
    slides.writes_text_to_shape(
        objectId=title_obj_id, text="Survey Notes", default_index=0
    )
    slides.writes_text_to_shape(
        objectId=subtitle_obj_id,
        text="Updated: " + date.today().strftime("%B %d, %Y"),
        default_index=0,
    )

    ic(slides.df)


if __name__ == "__main__":
    Fire(main)