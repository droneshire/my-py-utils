import re
import typing as T

import yagmail

from ryutils import log


class Email(T.TypedDict):
    address: str
    password: str
    quiet: bool


def is_valid_email(email: str) -> bool:
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    return re.fullmatch(regex, email) is not None


def get_email_accounts_from_password(
    emails: T.List[T.Dict[str, str]],
    dry_run: bool = False,
) -> T.List[Email]:
    email_accounts = []
    for email_account in emails:
        assert email_account["password"], "Missing password!"
        email_password = email_account["password"]
        email_accounts.append(
            Email(
                address=email_account["user"],
                password=email_password,
                quiet=dry_run,
            )
        )
    return email_accounts


def send_email_raw(
    email: Email,
    to_addresses: T.List[str],
    subject: str,
    content: str,
    attachments: T.Optional[T.List[str]] = None,
    verbose: bool = False,
) -> None:
    with yagmail.SMTP(email["address"], email["password"]) as email_sender:
        if isinstance(to_addresses, str):
            to_addresses = [to_addresses]
        email_sender.send(
            to=to_addresses,
            subject=subject,
            contents=content,
            attachments=attachments,
        )
        if verbose:
            log.print_ok(f"To: {', '.join(to_addresses)}\nFrom: {email['address']}")
            log.print_ok(f"Subject: {subject}")
            log.print_ok(f"{content}")


def send_email(
    emails: T.List[Email],
    to_addresses: T.List[str],
    subject: str,
    content: str,
    attachments: T.Optional[T.List[str]] = None,
    verbose: bool = False,
) -> bool:
    """
    Given a list of emails, try to send a the email from one of the accounts.
    Multiple emails helps in the case you are getting throttled from sending too many emails
    from one account.

    This method should not be used to send a the same email to many accounts. That should be done
    outside this method by calling this method multiple times.
    """

    for email in emails:
        if email["quiet"]:
            continue

        try:
            send_email_raw(
                email,
                to_addresses,
                subject,
                content,
                attachments=attachments,
                verbose=verbose,
            )
            return True
        except Exception as exception:  # pylint: disable=broad-except
            log.print_fail(
                f"Failed to send email alert for {' '.join(to_addresses)} "
                f"because of exception: {exception}"
            )
            continue

    return False
