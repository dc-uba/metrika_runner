
from metrika.database import Database
from metrika.experiment import Experiment
from metrika.plotter import Plotter

import argparse
import socket
import sys


class Engine:
    def __init__(self):
        # hook to be able to have 'run' as default command
        argparse.ArgumentParser.set_default_subparser = set_default_subparser

        self.experiments = {}
        self.arguments = self.parse_arguments()
        self.database = Database(self.arguments.testbed)
        self.plotter = None

    def organize_experiment(self, suite, name=None):
        experiment = Experiment(suite, name)
        self.experiments[experiment.name] = experiment
        return experiment

    def go(self):
        self.filter_experiments()
        self.arguments.func()

    def run_command(self):
        self.run()
        if not self.arguments.quiet:
            self.report()

        self.plot()

    def report_command(self):
        self.report()

    def plot_command(self):
        self.plot()

    def existing_results_of(self, experiments):
        return self.database.stored_results_of(experiments)

    def reject_already_measured_in(self, experiments):
        return self.database.reject_already_measured_in(experiments.values())

    def filter_experiments(self):
        if self.arguments.experiment:
            name = self.arguments.experiment
            self.experiments = {name: self.experiments[name]}

        for experiment in self.experiments.values():
            experiment.restrict(self.arguments)

        if self.arguments.force:
            self.work = {experiment: experiment.instances() for experiment in self.experiments.values()}
        else:
            self.work = self.reject_already_measured_in(self.experiments)

        self.done = [x for x in self.experiments.values() if x.name not in self.work]

    def run(self):

        print("experiments to run: " + str(self.work))
        print("experiments skipped: " + str(self.done))

        old_results = self.existing_results_of(self.done)
        sorted_work = sorted(self.work, key=lambda exp: exp.name)
        new_results = {experiment: experiment.run(self.arguments) for experiment in sorted_work}

        all_results = dict(old_results)
        all_results.update(new_results)
        self.database.save(new_results)

    def report(self):
            for name, exp in sorted_items(self.experiments):
                results = self.existing_results_of([exp])
                for i, measure_name in enumerate(exp.measures):
                    try:
                        exp.report(name + ' ' + measure_name, results, i)
                    except Exception:
                        print("Failed to write a report")

    def plot(self):
        #try:
            for name, exp in sorted_items(self.experiments):
                results = self.existing_results_of([exp])
                for i, measure_name in enumerate(exp.measures):
                    exp.plot(name + ' ' + measure_name, results, i)
                    pass

            if self.plotter is not None:
                results = self.existing_results_of(self.experiments.values())
                self.plotter.run_with(results, 'all', 0)
        #except Exception:
        #    print("Failed to output plot")

    def set_plotter(self, configurator, name, description):
        self.plotter = Plotter(configurator, name, description)

    def parse_arguments(self):
        parser = argparse.ArgumentParser(prog='Metrika', description='A scientifically rigorous measurement tool')
        parser.add_argument('-v', '--verbose', action='store_true', help='show more output')
        parser.add_argument('-b', '--bench', help='restrict to only specified benchs')
        parser.add_argument('--testbed', default=self.machine_name, help='name for the platform where we are running')
        subparsers = parser.add_subparsers(help='possible commands')

        parser_run = subparsers.add_parser('run', help='measure runs')
        parser_run.add_argument('-i', '--invocations', type=int, default=5, help='number of invocations')
        # parser_run.add_argument('-I', '--iterations', type=int, default=5, help='number of iterations')
        parser_run.add_argument('-x', '--experiment', help='experiment name')
        parser_run.add_argument('-f', '--force', action='store_true',
                                help='force measuring again even if results are already in database')
        parser_run.add_argument('-q', '--quiet', action='store_true', help='do not show summary of results')
        parser_run.add_argument('-s', '--show-output', action='store_true',
                                help='show output of programs being run in stdout')
        parser_run.add_argument('-e', '--hide-errors', action='store_true',
                                help='hide errors of programs being run')
        parser_run.add_argument('-r', '--restrict', help='restrict a variable to a value')
        parser_run.set_defaults(func=self.run_command)

        parser_report = subparsers.add_parser('report', help='report measures given results database, without running\n'
                                                             ' benchs again')
        parser_report.add_argument('-r', '--restrict', help='restrict a variable to a value')
        parser_report.set_defaults(func=self.report_command)

        parser_plot = subparsers.add_parser('plot', help='plot results from database contents')
        parser_plot.add_argument('-r', '--restrict', help='restrict a variable to a value')
        parser_plot.set_defaults(func=self.plot_command)

        if len(sys.argv) < 2:
            parser.print_usage()
            sys.exit(1)
        return parser.parse_args()

    @property
    def machine_name(self):
        return socket.gethostname()


def set_default_subparser(self, name, args=None):
    """default subparser selection. Call after setup, just before parse_args()
    name: is the name of the subparser to call by default
    args: if set is the argument list handed to parse_args()

    , tested with 2.7, 3.2, 3.3, 3.4
    it works with 2.6 assuming argparse is installed
    """
    subparser_found = False
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:  # global help if no subparser
            break
    else:
        for x in self._subparsers._actions:
            if not isinstance(x, argparse._SubParsersAction):
                continue
            for sp_name in x._name_parser_map.keys():
                if sp_name in sys.argv[1:]:
                    subparser_found = True
        if not subparser_found:
            # insert default in first position, this implies no
            # global options without a sub_parsers specified
            if args is None:
                sys.argv.insert(1, name)
            else:
                args.insert(0, name)


def sorted_items(dictionary):
    return sorted(dictionary.items(), key=lambda keyval: keyval[0])


