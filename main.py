from fire import Fire
from github import Github
from dotenv import load_dotenv
import os
import mistune
from bs4 import BeautifulSoup
from rich import inspect

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


class Slides:
    def __init__(self):
        pass

    def add_slide(self, slide):
        pass


class Slide:
    def __init__(self):
        self.title = None
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

    # Convert issues to padas dataframe
    for issue in issues:
        slide = Slide().from_issue(issue)
        inspect(slide)


if __name__ == "__main__":
    Fire(main)