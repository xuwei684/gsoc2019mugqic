#!/usr/bin/env python

# Python Standard Modules
import logging
import math
import os
import re
import sys

# Append mugqic_pipelines directory to Python library path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))))

# MUGQIC Modules
from core.config import *
from core.job import *
from core.pipeline import *
from bfx.design import *

from bfx import gq_seq_utils
from bfx import picard
from bfx import samtools
from pipelines.dnaseq import dnaseq

log = logging.getLogger(__name__)

class ChipSeq(dnaseq.DnaSeq):
    """
    ChIP-Seq Pipeline
    =================

    ChIP-Seq experiments allows the Isolation and sequencing of genomic DNA bound by a specific transcription factor,
    covalently modified histone, or other nuclear protein. The pipeline starts by trimming adaptors and
    low quality bases and mapping the reads (single end or paired end ) to a reference genome using bwa.
    Reads are filtered by mapping quality and duplicate reads are marked. Then, Homer quality control routines
    are used to provide information and feedback about the quality of the experiment. Peak calls is executed by MACS
    and annotation and motif discovery for narrow peaks are executed using Homer. Statistics of annotated peaks
    are produced for narrow peaks and a standard report is generated.

    An example of the ChIP-Seq report for an analysis on public ENCODE data is available for illustration purpose only:
    [DNA-Seq report](http://gqinnovationcenter.com/services/bioinformatics/tools/chipReport/index.html).

    [Here](https://bitbucket.org/mugqic/mugqic_pipelines/downloads/MUGQIC_Bioinfo_ChIP-Seq.pptx)
    is more information about ChIP-Seq pipeline that you may find interesting.
    """

    def __init__(self):
        # Add pipeline specific arguments
        self.argparser.add_argument("-d", "--design", help="design file", type=file)
        super(ChipSeq, self).__init__()

    def picard_mark_duplicates(self):
        """
        Mark duplicates. Aligned reads per sample are duplicates if they have the same 5' alignment positions
        (for both mates in the case of paired-end reads). All but the best pair (based on alignment score)
        will be marked as a duplicate in the BAM file. Marking duplicates is done using [Picard](http://broadinstitute.github.io/picard/).
        """

        jobs = []
        for sample in self.samples:
            alignment_file_prefix = os.path.join("alignment", sample.name, sample.name + ".")
            input = alignment_file_prefix + "sorted.bam"
            output = alignment_file_prefix + "sorted.dup.bam"
            metrics_file = alignment_file_prefix + "sorted.dup.metrics"

            job = picard.mark_duplicates([input], output, metrics_file)
            job.name = "picard_mark_duplicates." + sample.name
            jobs.append(job)
        return jobs

    def homer_make_tag_directory(self):
        """
        The Homer Tag directories, used to check for quality metrics, are computed at this step. 
        """

        jobs = []
        for sample in self.samples:
            alignment_file = os.path.join("alignment", sample.name, sample.name + ".sorted.bam")
            output_dir = os.path.join("tags", sample.name)

            jobs.append(Job(
                [alignment_file],
                [os.path.join(output_dir, "tagInfo.txt")],
                [['homer_make_tag_directory', 'module_homer']],
                command="""\
makeTagDirectory \\
  {output_dir} \\
  {alignment_file} \\
  -checkGC -genome {genome_fasta}""".format(
                    output_dir=output_dir,
                    alignment_file=alignment_file,
                    genome_fasta=config.param('homer_make_tag_directory', 'genome_fasta', type='filepath')
                ),
                name="homer_make_tag_directory." + sample.name
            ))

        return jobs

    def qc_plots_R(self):
        """
        Sequencing quality metrics as tag count, tag autocorrelation, sequence bias and GC bias are generated.
        """

         # If --design <design_file> option is missing, self.contrasts call will raise an Exception
        if self.contrasts:
            design_file = os.path.relpath(self.args.design.name, self.output_dir)

        return [Job(
            [design_file] + [os.path.join("tags", sample.name, "tagInfo.txt") for sample in self.samples],
            [os.path.join("graphs", sample.name + "_QC_Metrics.ps") for sample in self.samples],
            [
                ['qc_plots_R', 'module_mugqic_tools'],
                ['qc_plots_R', 'module_R']
            ],
            command="""\
mkdir -p graphs && \\
Rscript $R_TOOLS/chipSeqGenerateQCMetrics.R \\
  {design_file} \\
  {output_dir}""".format(
                design_file=design_file,
                output_dir=self.output_dir
            ),
            name="qc_plots_R"
        )]

    def gq_seq_utils_report(self):
        """
        Generate the standard report. A summary html report is automatically generated by the pipeline.
        This report contains description of the sequencing experiment as well as a detailed presentation
        of the pipeline steps and results. Various Quality Control (QC) summary statistics are included
        in the report and additional QC analysis is accessible for download directly through the report.
        The report includes also the main references of the software and methods used during the analysis,
        together with the full list of parameters passed to the pipeline main script.
        """

        job = gq_seq_utils.report(
            [config_file.name for config_file in self.args.config],
            self.output_dir,
            "DNAseq",
            self.output_dir
        )
        job.input_files = [
            "metrics/trimming.stats",
            "metrics/SampleMetrics.stats",
            "metrics/allSamples.SNV.SummaryTable.tsv",
            "metrics/allSamples.SNV.EffectsFunctionalClass.tsv",
            "metrics/allSamples.SNV.EffectsImpact.tsv"
        ]
        job.name = "gq_seq_utils_report"
        return [job]

    @property
    def steps(self):
        return [
            self.picard_sam_to_fastq,
            self.trimmomatic,
            self.merge_trimmomatic_stats,
            self.bwa_mem_picard_sort_sam,
            self.picard_merge_sam_files,
            self.picard_mark_duplicates,
            self.homer_make_tag_directory,
            self.qc_plots_R,
            self.gq_seq_utils_report
        ]

if __name__ == '__main__': 
    ChipSeq()
