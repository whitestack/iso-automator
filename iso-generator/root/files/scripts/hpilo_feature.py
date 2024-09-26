#!/usr/bin/env python3.8

import hpilo
import click
import logging


@click.command()
@click.option("--host", help="IP address of HP ILO server", required=True)
@click.option("--user", help="Username of HP ILO server", required=True)
@click.option(
    "--password", help="Password of the user of the HP ILO server", required=True
)
@click.option("--feature", help="Features to enable of the user", required=False)
@click.option("--status", help="Give status of the user", is_flag=True, required=False)
@click.option(
    "--action", type=click.Choice(["enable", "disable"], case_sensitive=False)
)
def enable(host, user, password, feature, status, action):
    """Simple program that enables or disables a feature in HP ILO user."""

    # Get status of user in HP ILO
    def get_status(ilo, user):
        print(f"Actual status {host} ({user})\n-------------------")

        status_user = ilo.get_user(user)

        for item in status_user:
            logging.info(f"- {item}: {status_user[item]}")

    # Creates the session
    ilo = hpilo.Ilo(host, user, password)

    if action is None and status:
        get_status(ilo, user)

    if action is not None and feature is not None:
        get_status(ilo, user)

        if action == "enable":
            change = True

        elif action == "disable":
            change = False

        data = {"user_login": user, feature: change}

        logging.info(f"Modifying user {user} : {feature} -> {change}\n")

        ilo.mod_user(**data)  # Modifies the feature of the user

        get_status(ilo, user)


if __name__ == "__main__":
    enable()  # pylint: disable=E1120
