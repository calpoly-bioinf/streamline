# Create your tasks here

import os
from celery import shared_task
from django.conf import settings
from . import job
import json
import requests
import subprocess
import csv
import sys
import os
import time
import pandas as pd

@shared_task
def streamline(job_id):
    print('handling streamline_web job', job_id)
    streamline_job = job.Job(job_id)
    streamline_job.load()

    try:   
        streamline_job.started_status()
        fasta, genome, chromosome = streamline_job.get_streamline_files()
        print(f'using |{fasta}| |{genome}| |{chromosome}|')
        os.system("mkdir temp")
        os.system("java -Xmx4g -jar FlashFry-assembly-1.12.jar index --tmpLocation ./temp --database " + chromosome + "_database --reference chromosomes/"+ genome + "/"+ chromosome + ".fa.gz --enzyme spcas9ngg")
        os.system("java -Xmx4g -jar FlashFry-assembly-1.12.jar discover --database " + chromosome + "_database --fasta " + fasta + " --output flashfry.output --positionOutput")

        # do pipeline stuff
        f = open("flashfry.output", "r")
        f.readline()  # first line in file is header (unecessary)
        line = f.readline()
        track = "clinvarMain"

        # get rid of slashes
        chromosome = chromosome[1:]
        genome = genome[1:]

        path = streamline_job.job_data_directory + "/" + streamline_job.job_id
        txt_file = open(path+"/streamline_web-results.txt", 'w')
        csv_file = open(path + '/streamline_web-results.csv', 'w', newline='')
        csv_writer = csv.writer(csv_file)
        headerBool = True
        while line:
            line = line.split()
            start = line[1]
            end = line[2]
            diff = int(end) - int(start)
            offtargets = line[8].split(",")

            for offtarget in offtargets:
                # this gets start num and direction, direction not used
                pair = offtarget.split(":")[1].split("^")
                start = pair[0]
                end = str(int(start) + diff)

                api_url = "https://api.genome.ucsc.edu/getData/track?genome=" + genome + ";track=" + track + ";chrom=" + chromosome + ";start=" + start + ";end=" + end + ""

                # time.sleep(0.5)

                response = requests.get(api_url)
                output_dump = response.json()
                print(f'using |{api_url}| |{output_dump}|')

                mutations = output_dump["clinvarMain"]
                if mutations != []:
                    for mutation in mutations:
                        print("mutation: " + mutation["clinSign"])
                        print(json.dumps(mutation))

                        #to text file
                        json.dump(mutation, txt_file, indent=4)

                        #to csv file
                        if headerBool == False:
                            # values = mutation.values()
                            values = [mutation["chrom"], mutation["chromStart"], mutation["chromEnd"], mutation["name"],
                                      mutation["score"], mutation["strand"], mutation["origName"], mutation["clinSign"],
                                      mutation["type"], mutation["geneId"], mutation["molConseq"], mutation["snpId"],
                                      mutation["phenotypeList"], mutation["phenotype"], mutation["_jsonHgvsTable"]]
                            csv_writer.writerow(values)

                        else:
                            headerBool = False
                            # headers = mutation.keys()
                            headers = ["chrom", "chromStart", "chromEnd", "name", "score", "strand", "origName",
                                       "clinSign",
                                       "type", "geneId", "molConseq", "snpId", "phenotypeList", "phenotype",
                                       "_jsonHgvsTable"]
                            csv_writer.writerow(headers)
            line = f.readline()
        txt_file.close()
        csv_file.close()

        with open(path+"/streamline_web-results.txt", 'r') as read_obj:
            first_char = read_obj.read(1)
            if first_char:
                # there is data to write
                df = pd.read_csv(path + '/streamline_web-results.csv')
                writer = pd.ExcelWriter(path + '/streamline_web-results.xlsx')
                df.to_excel(writer, index=None, header=True)
                writer.save()
            else:
                # there is no data to write
                df = pd.DataFrame()
                writer = pd.ExcelWriter(path + '/streamline_web-results.xlsx')
                df.to_excel(writer, index=None, header=True)
                writer.save()
        print('finished streamline_web job')
        streamline_job.completed_status()

    except Exception as e:
        streamline_job.error_status(f"Unexpected exception {e=}")
