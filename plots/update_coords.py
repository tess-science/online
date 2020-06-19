#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import json
from datetime import datetime

import googlemaps
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_creds(config):
    return service_account.Credentials.from_service_account_file(
        "auth.json", scopes=SCOPES
    )


def get_service(config):
    return build("sheets", "v4", credentials=get_creds(config)).spreadsheets()


def get_sheet(config):
    values = (
        get_service(config)
        .values()
        .get(spreadsheetId=config["sheet_id"], range=config["sheet_name"])
        .execute()
        .get("values", [])
    )
    return values


def main():
    date = datetime(year=2020, month=9, day=8)

    with open("secrets.json", "r") as f:
        secrets = json.load(f)

    values = get_sheet(secrets)
    gmaps = googlemaps.Client(key=secrets["api_key"])

    for i in range(1, len(values)):
        row = values[i]
        row += [""] * (9 - len(row))
        if row[6]:
            continue
        loc = gmaps.geocode(row[3])
        if not loc:
            row[6] = "unknown"
            continue

        loc = loc[0]["geometry"]["location"]
        row[6] = "{0[lat]}, {0[lng]}".format(loc)

        try:
            tz = gmaps.timezone((loc["lat"], loc["lng"]), date)
        except googlemaps.exceptions.ApiError:
            print("waiting...")
            time.sleep(10.0)
            tz = gmaps.timezone((loc["lat"], loc["lng"]), date)

        row[7] = tz["timeZoneId"]
        row[8] = (tz["dstOffset"] + tz["rawOffset"]) / 3600
        print(row)

    body = dict(values=values)
    get_service(secrets).values().update(
        spreadsheetId=secrets["sheet_id"],
        range=secrets["sheet_name"],
        body=body,
        valueInputOption="RAW",
    ).execute()


if __name__ == "__main__":
    main()
