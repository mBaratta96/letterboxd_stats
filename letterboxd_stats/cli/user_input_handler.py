import pandas as pd
from datetime import datetime

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

def _validate_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return False
    return True

class UserInputHandler:

    @staticmethod
    def user_choose_option_lb_lists(options: list[str]) -> str:
        result = inquirer.fuzzy(  # type: ignore
            message="Select your list:",
            mandatory=True,
            max_height="25%",
            choices=options,
            validate=lambda result: result in options,
        ).execute()
        return result
    
    @staticmethod
    def user_choose_option_search_result(options: list[str]) -> int:
        choices = [Choice(i, name=r) for i, r in enumerate(options)]
        result = inquirer.select(  # type: ignore
            message="Result of your search. Please select one",
            choices=choices,
            default=choices[0],
        ).execute()
        return result
    
    @staticmethod
    def user_choose_options_multiple(options: list[str]) -> list[str]:
        result = inquirer.checkbox(
            message="Pick a desired value (or select 'all'). Use space to toggle your choices. Press Enter to confirm.",
            choices=[Choice(option, enabled=True) for option in options],  # Pre-select all
            validate=lambda result: len(result) > 0,  # Ensure at least one option is selected
        ).execute()
        return result

    @staticmethod
    def user_choose_option(options: list[str], message: str, default: str | None = None) -> str:
        result = inquirer.select(  # type: ignore
            message=message,
            choices=options,
            default=default or options[0],
        ).execute()
        return result

    @staticmethod
    def user_choose_film_from_list(film_titles: pd.Series, film_ids: pd.Series) -> str:
        result = inquirer.fuzzy(  # type: ignore
            message="Select film for more information:",
            mandatory=False,
            max_height="25%",
            choices=[Choice(value=film_id, name=film_title) for film_id, film_title in zip(film_ids, film_titles)],
            keybindings={"skip": [{"key": "escape"}]},
            invalid_message="Input not in list of films.",
            validate=lambda selected_id: selected_id in film_ids.values,
        ).execute()
        return result

    @staticmethod
    def user_choose_film_from_dataframe(df: pd.DataFrame) -> pd.Series | None:
        film_id = UserInputHandler.user_choose_film_from_list(df["Title"], df.index.to_series())
        if film_id is None:
            return None
        film_row = df.loc[film_id]
        return film_row
    

    @staticmethod
    def user_create_diary_entry_payload() -> dict[str, str]:
        print("Set all the infos for the film:\n")
        specify_date = inquirer.confirm(message="Specify date?").execute()  # type: ignore
        today = datetime.today().strftime("%Y-%m-%d")
        get_specified_date = inquirer.text(  # type: ignore
            message="Set viewing date:",
            default=today,
            validate=lambda d: _validate_date(d),
            invalid_message="Wrong date format",
        )
        specified_date = get_specified_date.execute() if specify_date else today
        stars = inquirer.number(  # type: ignore
            message="How many stars? (Only values from 0 to 5)",
            float_allowed=True,
            min_allowed=0.0,
            max_allowed=5.0,
            validate=lambda n: (2 * float(n)).is_integer(),
            invalid_message="Wrong value. Either an integer or a .5 float",
            replace_mode=True,
            filter=lambda n: int(2 * float(n)),
        ).execute()
        liked = inquirer.confirm(message="Give this film a ♥?").execute()  # type: ignore
        leave_review = inquirer.confirm(message="Leave a review?").execute()  # type: ignore
        review = inquirer.text(  # type: ignore
            message="Write a review. "
            + "Use HTML tags for formatting (<b>, <i>, <a href='[URL]'>, <blockquote<>). "
            + "Press Enter for multiline.",
            multiline=True,
        ).execute() if leave_review else ""
        contains_spoilers = False
        if len(review) > 0:
            contains_spoilers = inquirer.confirm(message="The review contains spoilers?").execute()  # type: ignore
        rewatch = inquirer.confirm(message="Have you seen this film before?").execute()  # type: ignore
        payload = {
            "specifiedDate": specify_date,
            "viewingDateStr": specified_date,
            "rating": stars,
            "liked": liked,
            "review": review,
            "containsSpoilers": contains_spoilers,
            "rewatch": rewatch,
        }
        if len(review.strip().rstrip("\n")) > 0 or specify_date:
            tags = inquirer.text(message="Add some comma separated tags. Or leave this empty.").execute()  # type: ignore
            payload["tag"] = (tags.split(",") if "," in tags else tags) if len(tags) > 0 else ""
        return payload