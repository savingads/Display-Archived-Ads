# Display Archived Ads
This tool is used for displaying ads from a WARC file and it shows the live version of an ad beside the archived version. Currently this tool displays web resources that could be associated with an ad. In the future we plan on automatically identifying ad resources by checking if the URIs are from a known ad service.

General structure for the command used for this tool:
```
python3 Display_Archived_Ads.py /path/to/WARC/file.warc <seed URL>
```

Example command used for an IGN web page:
```
python3 Display_Archived_Ads.py data.warc.gz https://www.ign.com/tv/the-last-of-us-the-series
```
