from __future__ import print_function
import matplotlib
matplotlib.use('Agg')
import flask  # import Flask, render_template, send_from_directory
from rllab.misc.ext import flatten
from rllab.viskit import core
from rllab.misc import ext
import sys
import argparse
import json
import numpy as np
# import threading, webbrowser
import plotly.offline as po
import plotly.graph_objs as go


def sliding_mean(data_array, window=5):
    data_array = np.array(data_array)
    new_list = []
    for i in range(len(data_array)):
        indices = range(max(i - window + 1, 0),
                        min(i + window + 1, len(data_array)))
        avg = 0
        for j in indices:
            avg += data_array[j]
        avg /= float(len(indices))
        new_list.append(avg)

    return np.array(new_list)
import itertools

app = flask.Flask(__name__, static_url_path='/static')

exps_data = None
plottable_keys = None
distinct_params = None


@app.route('/js/<path:path>')
def send_js(path):
    return flask.send_from_directory('js', path)


@app.route('/css/<path:path>')
def send_css(path):
    return flask.send_from_directory('css', path)


def make_plot(plot_list, use_median=False):
    data = []
    for idx, plt in enumerate(plot_list):
        color = core.color_defaults[idx % len(core.color_defaults)]
        if use_median:
            x = range(len(plt.percentile50))
            y = list(plt.percentile50)
            y_upper = list(plt.percentile75)
            y_lower = list(plt.percentile25)
        else:
            x = range(len(plt.means))
            y = list(plt.means)
            y_upper = list(plt.means + plt.stds)
            y_lower = list(plt.means - plt.stds)

        data.append(go.Scatter(
            x=x + x[::-1],
            y=y_upper + y_lower[::-1],
            fill='tozerox',
            fillcolor=core.hex_to_rgb(color, 0.2),
            line=go.Line(color='transparent'),
            showlegend=False,
            legendgroup=plt.legend,
            hoverinfo='none'
        ))
        data.append(go.Scatter(
            x=x,
            y=y,
            name=plt.legend,
            legendgroup=plt.legend,
            line=dict(color=core.hex_to_rgb(color)),
        ))

    layout = go.Layout(
        legend=dict(
            xanchor="auto",
            yanchor="auto",
        )
    )
    fig = go.Figure(data=data, layout=layout)
    return po.plot(fig, output_type='div', include_plotlyjs=False)


def make_plot_eps(plot_list, use_median=False, counter=0):
    import matplotlib.pyplot as _plt
    f, ax = _plt.subplots(figsize=(8, 4))
    for idx, plt in enumerate(plot_list):
        color = core.color_defaults[idx % len(core.color_defaults)]
        if use_median:
            x = range(len(plt.percentile50))
            y = list(plt.percentile50)
            y_upper = list(plt.percentile75)
            y_lower = list(plt.percentile25)
        else:
            x = range(len(plt.means))
            y = list(plt.means)
            y_upper = list(plt.means + plt.stds)
            y_lower = list(plt.means - plt.stds)
        print(plt.legend)
        if 'rllab.algos.trpo.TRPO' in plt.legend:
            plt.legend = 'TRPO'
        if 'sandbox.rein.algos.trpo_unn.TRPO' in plt.legend:
            plt.legend = 'TRPO+EX'
        ax.fill_between(
            x, y_lower, y_upper, interpolate=True, facecolor=color, linewidth=0.0, alpha=0.3)
        ax.plot(x, y, color=color, label=plt.legend)
        ax.grid(True)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        if counter == 1:
            ax.set_xlim([0, 200])
            #ax.set_ylim([0, 1600])
            loc = 'lower right'
        elif counter == 2:
            ax.set_xlim([0, 800])
            loc = 'lower right'
        elif counter == 3:
            ax.set_xlim([0, 1000])
            loc = 'lower right'
        elif counter == 4:
            ax.set_xlim([0, 120])
            loc= 'lower right'
        leg = ax.legend(loc=loc, prop={'size':12}, ncol=1)
        for legobj in leg.legendHandles:
            legobj.set_linewidth(5.0)
        _plt.savefig('tmp' + str(counter) + '.pdf')


def get_plot_instruction(plot_key, split_key=None, group_key=None, filters=None, use_median=False,
                         only_show_best=True, gen_eps=False):
    print(plot_key, split_key, group_key, filters)
    selector = core.Selector(exps_data)
    if filters is None:
        filters = dict()
    for k, v in filters.iteritems():
        selector = selector.where(k, str(v))
    # print selector._filters
    if split_key is not None:
        vs = [vs for k, vs in distinct_params if k == split_key][0]
        split_selectors = [selector.where(split_key, v) for v in vs]
        split_legends = map(str, vs)
    else:
        split_selectors = [selector]
        split_legends = ["Plot"]
    plots = []
    counter = 1
    for split_selector, split_legend in zip(split_selectors, split_legends):
        if group_key:
            vs = [vs for k, vs in distinct_params if k == group_key][0]
            group_selectors = [split_selector.where(group_key, v) for v in vs]
            group_legends = map(str, vs)
        else:
            group_selectors = [split_selector]
            group_legends = [split_legend]
        to_plot = []
        for group_selector, group_legend in zip(group_selectors, group_legends):
            filtered_data = group_selector.extract()
            if len(filtered_data) > 0:

                if only_show_best:
                    # Group by seed and sort.
                    # -----------------------
                    filtered_params = core.extract_distinct_params(
                        filtered_data, l=0)
                    filtered_params2 = [p[1] for p in filtered_params]
                    filtered_params_k = [p[0] for p in filtered_params]
                    product_space = list(itertools.product(
                        *filtered_params2
                    ))
                    data_best_regret = None
                    best_regret = -np.inf
                    for idx, params in enumerate(product_space):
                        selector = core.Selector(exps_data)
                        for k, v in zip(filtered_params_k, params):
                            selector = selector.where(k, str(v))
                        data = selector.extract()
                        if len(data) > 0:
                            progresses = [
                                exp.progress.get(plot_key, np.array([np.nan])) for exp in data]
                            sizes = map(len, progresses)
                            max_size = max(sizes)
                            progresses = [
                                np.concatenate([ps, np.ones(max_size - len(ps)) * np.nan]) for ps in progresses]

                            if use_median:
                                medians = np.nanmedian(progresses, axis=0)
                                regret = np.median(medians)
                            else:
                                means = np.nanmean(progresses, axis=0)
                                regret = np.mean(means)
                            if regret > best_regret:
                                best_regret = regret
                                data_best_regret = data
                            distinct_params_k = [p[0] for p in distinct_params]
                            distinct_params_v = [
                                v for k, v in zip(filtered_params_k, params) if k in distinct_params_k]
                            distinct_params_kv = [
                                (k, v) for k, v in zip(distinct_params_k, distinct_params_v)]
                            distinct_params_kv_string = str(
                                distinct_params_kv).replace('), ', ')\t')
                            print(
                                '{}\t{}\t{}'.format(regret, len(progresses), distinct_params_kv_string))

                    print(group_selector._filters)
                    print('best regret: {}'.format(best_regret))
                    # -----------------------
                    if best_regret != -np.inf:
                        progresses = [
                            exp.progress.get(plot_key, np.array([np.nan])) for exp in data_best_regret]
                        sizes = map(len, progresses)
                        # more intelligent:
                        max_size = max(sizes)
                        progresses = [
                            np.concatenate([ps, np.ones(max_size - len(ps)) * np.nan]) for ps in progresses]
                        legend = '{} ({:.1f})'.format(
                            group_legend, best_regret)
                        window_size = np.maximum(
                            int(np.round(max_size / float(1000))), 1)
                        if use_median:
                            percentile25 = np.nanpercentile(
                                progresses, q=25, axis=0)
                            percentile50 = np.nanpercentile(
                                progresses, q=50, axis=0)
                            percentile75 = np.nanpercentile(
                                progresses, q=75, axis=0)
                            percentile25 = sliding_mean(percentile25,
                                                        window=window_size)
                            percentile50 = sliding_mean(percentile50,
                                                        window=window_size)
                            percentile75 = sliding_mean(percentile75,
                                                        window=window_size)
                            to_plot.append(
                                ext.AttrDict(percentile25=percentile25, percentile50=percentile50,
                                             percentile75=percentile75, legend=legend))
                        else:
                            means = np.nanmean(progresses, axis=0)
                            stds = np.nanstd(progresses, axis=0)
                            means = sliding_mean(means,
                                                 window=window_size)
                            stds = sliding_mean(stds,
                                                window=window_size)
                            to_plot.append(
                                ext.AttrDict(means=means, stds=stds, legend=legend))
                else:
                    progresses = [
                        exp.progress.get(plot_key, np.array([np.nan])) for exp in filtered_data]
                    sizes = map(len, progresses)
                    # more intelligent:
                    max_size = max(sizes)
                    progresses = [
                        np.concatenate([ps, np.ones(max_size - len(ps)) * np.nan]) for ps in progresses]
                    if only_show_best:
                        legend = '{} ({:.1f})'.format(
                            group_legend, best_regret)
                    else:
                        legend = '{}'.format(
                            group_legend)
                    window_size = np.maximum(
                        int(np.round(max_size / float(1000))), 1)

                    if use_median:
                        percentile25 = np.nanpercentile(
                            progresses, q=25, axis=0)
                        percentile50 = np.nanpercentile(
                            progresses, q=50, axis=0)
                        percentile75 = np.nanpercentile(
                            progresses, q=75, axis=0)
                        percentile25 = sliding_mean(percentile25,
                                                    window=window_size)
                        percentile50 = sliding_mean(percentile50,
                                                    window=window_size)
                        percentile75 = sliding_mean(percentile75,
                                                    window=window_size)
                        to_plot.append(
                            ext.AttrDict(percentile25=percentile25, percentile50=percentile50,
                                         percentile75=percentile75, legend=group_legend))
                    else:
                        means = np.nanmean(progresses, axis=0)
                        stds = np.nanstd(progresses, axis=0)
                        means = sliding_mean(means,
                                             window=window_size)
                        stds = sliding_mean(stds,
                                            window=window_size)
                        to_plot.append(
                            ext.AttrDict(means=means, stds=stds, legend=group_legend))

        if len(to_plot) > 0 and not gen_eps:
            plots.append("<div>%s: %s</div>" % (split_key, split_legend))
            plots.append(make_plot(to_plot, use_median=use_median))

        if gen_eps:
            make_plot_eps(to_plot, use_median=use_median, counter=counter)
        counter += 1
    return "\n".join(plots)


@app.route("/plot_div")
def plot_div():
    args = flask.request.args
    plot_key = args.get("plot_key")
    split_key = args.get("split_key", "")
    group_key = args.get("group_key", "")
    filters_json = args.get("filters", "{}")
    filters = json.loads(filters_json)
    if len(split_key) == 0:
        split_key = None
    if len(group_key) == 0:
        group_key = None
    # group_key = distinct_params[0][0]
    # print split_key
    # exp_filter = distinct_params[0]
    use_median = args.get("use_median", "") == 'True'
    gen_eps = args.get("eps", "") == 'True'
    plot_div = get_plot_instruction(plot_key=plot_key, split_key=split_key,
                                    group_key=group_key, filters=filters, use_median=use_median, gen_eps=gen_eps)
    # print plot_div
    return plot_div


@app.route("/")
def index():
    # exp_folder_path = "data/s3/experiments/ppo-atari-3"
    # _load_data(exp_folder_path)
    # exp_json = json.dumps(exp_data)
    if "AverageReturn" in plottable_keys:
        plot_key = "AverageReturn"
    elif len(plottable_keys) > 0:
        plot_key = plottable_keys[0]
    else:
        plot_key = None
    if len(distinct_params) > 0:
        group_key = distinct_params[0][0]
    else:
        group_key = None
    plot_div = get_plot_instruction(
        plot_key=plot_key, split_key=None, group_key=group_key)
    return flask.render_template(
        "main.html",
        plot_div=plot_div,
        plot_key=plot_key,
        group_key=group_key,
        plottable_keys=plottable_keys,
        distinct_param_keys=[str(k) for k, v in distinct_params],
        distinct_params=dict([(str(k), map(str, v))
                              for k, v in distinct_params]),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path", type=str)
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args(sys.argv[1:])
    print("Importing data from {path}...".format(path=args.data_path))
    exps_data = core.load_exps_data(args.data_path)
    plottable_keys = list(
        set(flatten(exp.progress.keys() for exp in exps_data)))

    distinct_params = core.extract_distinct_params(exps_data)
    port = 5000
    url = "http://127.0.0.1:{0}".format(port)
    print("Done! View http://localhost:5000 in your browser")
    app.run(debug=args.debug)
