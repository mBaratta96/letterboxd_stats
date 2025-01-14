"""
User Interaction Module
=======================

This module provides utility functions for prompting users via a command-line
interface. It leverages the `InquirerPy` library to prompt users with options,
validate inputs, and collect data for operations such as selecting films,
providing ratings, and creating diary entries.

"""
from datetime import datetime

import pandas as pd
from InquirerPy import inquirer
from InquirerPy.base.control import Choice


def _validate_date(s: str) -> bool:
    """Validates whether a string is in the format 'YYYY-MM-DD'.
    """
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def user_choose_option_lb_lists(options: list[str]) -> str:
    """
    Prompts the user to select an option from a list of Letterboxd lists.

    Args:
        options (list[str]): List of options to choose from.

    Returns:
        str: The selected option.
    """
    result = inquirer.fuzzy(  # type: ignore
        message="Select your list:",
        mandatory=True,
        max_height="25%",
        choices=options,
        validate=lambda result: result in options,
    ).execute()
    return result


def user_choose_option_search_result(options: list[str]) -> int:
    """
    Prompts the user to select an option from search results.

    Args:
        options (list[str]): List of search result options.

    Returns:
        int: Index of the selected option.
    """
    choices = [Choice(i, name=r) for i, r in enumerate(options)]
    result = inquirer.select(  # type: ignore
        message="Result of your search. Please select one",
        choices=choices,
        default=choices[0],
    ).execute()
    return result


def user_choose_options_multiple(options: list[str]) -> list[str]:
    """
    Prompts the user to select multiple options from a list.

    Args:
        options (list[str]): List of options to choose from.

    Returns:
        list[str]: List of selected options.
    """
    result = inquirer.checkbox(
        message="Pick a desired value (or select 'all'). \
                Use space to toggle your choices. \
                Press Enter to confirm.",
        choices=[Choice(option, enabled=True) for option in options],  # Pre-select all
        validate=lambda result: len(result)
        > 0,  # Ensure at least one option is selected
    ).execute()
    return result


def user_choose_option(
    options: list[str], message: str, default: str | None = None
) -> str:
    """
    Prompts the user to select an option with a custom message.

    Args:
        options (list[str]): List of options to choose from.
        message (str): Prompt message.
        default (str | None): Default option. Defaults to the first option.

    Returns:
        str: The selected option.
    """
    result = inquirer.select(  # type: ignore
        message=message,
        choices=options,
        default=default or options[0],
    ).execute()
    return result


def user_choose_film_from_list(film_titles: pd.Series, film_ids: pd.Series) -> str:
    """
    Prompts the user to select a film from a list using fuzzy search.

    Args:
        film_titles (pd.Series): Series of film titles.
        film_ids (pd.Series): Series of film IDs.

    Returns:
        str: ID of the selected film.
    """
    result = inquirer.fuzzy(  # type: ignore
        message="Select film for more information: (type to narrow your search)",
        mandatory=False,
        max_height="25%",
        choices=[
            Choice(value=film_id, name=film_title)
            for film_id, film_title in zip(film_ids, film_titles)
        ],
        keybindings={"skip": [{"key": "escape"}]},
        invalid_message="Input not in list of films.",
        validate=lambda selected_id: selected_id in film_ids.values,
    ).execute()
    return result


def user_choose_film_from_dataframe(df: pd.DataFrame) -> pd.Series | None:
    """
    Prompts the user to select a film from a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing film titles and IDs.

    Returns:
        pd.Series | None: Row of the selected film or None if no selection was made.
    """
    film_id = user_choose_film_from_list(df["Title"], df.index.to_series())
    if film_id is None:
        return None
    film_row = df.loc[film_id]
    return film_row


def user_choose_rating():
    """
    Prompts the user to provide a star rating from 0 to 5.

    Returns:
        int: The selected rating as an integer (e.g., 3.5 -> 7).
    """
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
    return stars


def user_create_diary_entry_payload() -> dict[str, str]:
    """
    Prompts the user to create a payload for a Letterboxd diary entry.

    Includes options for specifying the date, rating, liking the film, leaving a review,
    and tagging the entry.

    Returns:
        dict[str, str]: Dictionary containing the diary entry payload.
    """
    specify_date = inquirer.confirm(message="Specify date?").execute()  # type: ignore
    today = datetime.today().strftime("%Y-%m-%d")
    get_specified_date = inquirer.text(  # type: ignore
        message="Set viewing date:",
        default=today,
        validate=_validate_date,
        invalid_message="Wrong date format",
    )
    specified_date = get_specified_date.execute() if specify_date else today
    stars = user_choose_rating()
    liked = inquirer.confirm(message="Give this film a ♥?").execute()  # type: ignore
    leave_review = inquirer.confirm(message="Leave a review?").execute()  # type: ignore
    review = (
        inquirer.text(  # type: ignore
            message="Write a review. "
            + "Use HTML tags for formatting (<b>, <i>, <a href='[URL]'>, <blockquote<>). "
            + "Press Enter for multiline.",
            multiline=True,
        ).execute()
        if leave_review
        else ""
    )
    contains_spoilers = False
    if len(review) > 0:
        message = "The review contains spoilers?"
        contains_spoilers = inquirer.confirm(message=message).execute()
    rewatch = inquirer.confirm(message="Have you seen this film before?").execute()
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
        message = "Add some comma separated tags. Or leave this empty."
        tags = inquirer.text(message=message).execute()
        payload["tag"] = (
            (tags.split(",") if "," in tags else tags) if len(tags) > 0 else ""
        )
    return payload
