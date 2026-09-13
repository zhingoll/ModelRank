"""Deliver the seven manuscript figures: reuse one schematic, redraw six plots.

Install numpy, pandas and matplotlib. Run:
    python figures.py --output /path/to/NEW/directory

To redraw only the six statistical figures:
    python figures.py --statistical-only --output /path/to/NEW/directory

This is figure reproduction, not a rerun of the underlying experiments.
The scatter input retains the original 7,000 LT sample (seed 42), all other
roles, inset points and labelled cases, with original draw order and full-
population P90 thresholds. The trajectory input has 58 observed model-months;
no missing month is interpolated. Figure 1 is a manually authored schematic:
its checksum-verified authoritative PDF is copied unchanged, NOT regenerated.
The editable SVG is supplied alongside it but is not converted by this command.
Existing output directories are refused. Inputs are checked before writing.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / 'data' / 'figures'
RQ1_RESULTS = DATA
FIGURES = None
SCHEMATIC = 'fig1_panel_a_overall_study_overview.pdf'


def save(fig, stem):
    fig.savefig(FIGURES / (stem + '.pdf'),
                metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


save_rq1 = save


def validate_inputs():
    manifest = json.loads((DATA / 'inputs.json').read_text(encoding='utf-8'))
    if SCHEMATIC not in manifest['sha256']:
        raise ValueError('Missing frozen schematic checksum')
    for name, digest in manifest['sha256'].items():
        path = DATA / name
        if path.parent != DATA or not path.is_file():
            raise ValueError('Missing or invalid plotting input: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen plotting input checksum mismatch: ' + name)
    frame = pd.read_csv(DATA / 'trajectories.csv', float_precision='round_trip')
    expected = {'nvidia/Minitron-4B-Base': 20,
                'black-forest-labs/FLUX.1-dev': 20,
                'Qwen/Qwen2.5-7B-Instruct': 18}
    if frame.groupby('model_id').size().to_dict() != expected or frame.duplicated(['model_id', 'month']).any():
        raise ValueError('Expected the exact three-model, 58-row trajectory panel')
    matrix = pd.read_csv(DATA / 'transitions.csv')
    roles = {'PR', 'HR', 'PL', 'LT'}
    if set(zip(matrix.source, matrix.target)) != {(a, b) for a in roles for b in roles} or len(matrix) != 16:
        raise ValueError('Expected all 16 transition cells exactly once')
    counts = Counter({(r.source, r.target): int(r.count) for r in matrix.itertuples()})
    if sum(counts.values()) != 8813341 or any(n < 0 for n in counts.values()):
        raise ValueError('Invalid frozen transition counts')
    return manifest, counts, frame


def main():
    global FIGURES
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', required=True, type=Path,
                        help='New directory only; never overwrites existing files')
    parser.add_argument('--statistical-only', action='store_true',
                        help='Reproduce six statistical figures; explicitly omit Figure 1')
    args = parser.parse_args()
    manifest, counts, trajectories = validate_inputs()
    FIGURES = args.output.resolve()
    FIGURES.mkdir(parents=True, exist_ok=False)
    if not args.statistical_only:
        shutil.copyfile(DATA / SCHEMATIC, FIGURES / SCHEMATIC)
    configure()
    rq1_type_figure()
    rq1_concentration_figure()
    figure5()
    figure6(counts)
    figure7(counts)
    styles = {'nvidia/Minitron-4B-Base': ('Minitron-4B-Base', '#d6604d', 'o'),
              'black-forest-labs/FLUX.1-dev': ('FLUX.1-dev', '#2166ac', 's'),
              'Qwen/Qwen2.5-7B-Instruct': ('Qwen2.5-7B', '#4daf4a', '^')}
    figure8(frame=trajectories, model_styles=styles)
    if args.statistical_only:
        print('Rendered 6 statistical figures. Figure 1 intentionally omitted.')
    else:
        print('Reused frozen Figure 1 (copied unchanged, not regenerated). '
              'Regenerated 6 statistical figures.')


# BEGIN EXTRACTED DRAWING FUNCTIONS
ROLE_NAMES = {'PR': 'Popular Roots', 'PL': 'Popular Leaves', 'HR': 'Hidden Roots', 'LT': 'Long Tail'}
ROLE_COLORS = {'PR': '#0072B2', 'PL': '#CC79A7', 'HR': '#D55E00', 'LT': '#4D4D4D'}
ROLE_MARKERS = {'PR': 'o', 'PL': 's', 'HR': '^', 'LT': 'X'}
ROLE_HATCHES = {'PR': '///', 'PL': '\\\\\\', 'HR': 'xxx', 'LT': '...'}
ROLE_ORDER = ['PR', 'PL', 'HR', 'LT']
FIGURE_STYLE_CONTRACT = {'figure5': {'figsize': (5.7, 5.0), 'inset_bounds': (0.36, 0.18, 0.37, 0.28), 'legend_loc': 'center right', 'legend_bbox': (0.985, 0.26), 'legend_columns': 1, 'long_tail_sample_n': 7000, 'long_tail_sample_seed': 42, 'long_tail_marker': 'X', 'long_tail_marker_size': 16, 'long_tail_marker_fill': 'solid'}, 'figure6': {'figsize': (4.5, 3.8), 'role_order': ('PR', 'HR', 'PL', 'LT'), 'cmap': 'YlOrRd', 'x_label': 'To role', 'y_label': 'From role', 'colorbar_label': 'Transition %'}, 'figure7': {'figsize': (10.0, 7.0), 'role_order': ('PR', 'HR', 'PL', 'LT'), 'node_count_format': 'comma-separated integer', 'flow_annotation_count_format': 'compact', 'title_scope': '20-month aggregate'}, 'figure8': {'figsize': (5.5, 5.0), 'legend_loc': 'upper left', 'line_style': '-', 'month_tick_format': 'YY-MM', 'panel_titles': ('(a) ModelRank score', '(b) Usage popularity')}}

def configure() -> None:
    plt.rcParams.update({'font.family': 'serif', 'font.size': 9, 'axes.labelsize': 10, 'axes.titlesize': 10, 'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 8, 'figure.dpi': 300, 'savefig.dpi': 300, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.05})

def short_month(month: str) -> str:
    (year, number) = str(month).split('-')
    return f'{year[2:]}-{number}'

def rq1_type_figure() -> None:
    frame = pd.read_csv(RQ1_RESULTS / 'rq1_type_evolution.csv')
    months = frame['month'].astype(str).tolist()
    labels = ['Fine-tune', 'Adapter', 'Quantized', 'Merge']
    columns = ['finetune_pct', 'adapter_pct', 'quantized_pct', 'merge_pct']
    colors = ['#0072B2', '#E69F00', '#009E73', '#CC79A7']
    hatches = ['///', '\\\\', 'xxx', '...']
    (fig, ax) = plt.subplots(figsize=(5.5, 2.8))
    areas = ax.stackplot(range(len(months)), *[frame[column].to_numpy() for column in columns], labels=labels, colors=colors, alpha=0.88)
    for (area, hatch) in zip(areas, hatches):
        area.set_hatch(hatch)
        area.set_edgecolor('white')
        area.set_linewidth(0.35)
    ax.set_xlim(0, len(months) - 1)
    ax.set_ylim(0, 100)
    ax.set_ylabel('Share of first-observed edges (%)')
    ticks = list(range(0, len(months), 3))
    ax.set_xticks(ticks)
    ax.set_xticklabels([short_month(months[i]) for i in ticks], rotation=45, ha='right')
    ax.legend(loc='upper right', ncol=2, framealpha=0.9)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save_rq1(fig, 'rq1_type_evolution')

def rq1_concentration_figure() -> None:
    frame = pd.read_csv(RQ1_RESULTS / 'rq1_concentration.csv')
    months = frame['month'].astype(str).tolist()
    x = np.arange(len(months))
    (fig, ax1) = plt.subplots(figsize=(7.0, 3.2))
    ax1.plot(x, frame['top50_share'], 's-', color='#C44E52', linewidth=1.8, markersize=5, label='Top-50 share', zorder=3)
    ax1.plot(x, frame['top10_share'], 'o-', color='#4C72B0', linewidth=1.8, markersize=5, label='Top-10 share', zorder=3)
    ax1.plot(x, frame['top1_share'], '^-', color='#55A868', linewidth=1.8, markersize=5, label='Top-1 share', zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels([short_month(month) for month in months], rotation=45, ha='right')
    ax1.set_ylabel('Share of first-observed edges (%)')
    ax1.set_ylim(0, 100)
    ax2 = ax1.twinx()
    ax2.bar(x, frame['n_active_bases'], color='#DDDDDD', alpha=0.5, width=0.6, label='Active parent models')
    ax2.set_ylabel('Active parent models', color='#888888')
    ax2.tick_params(axis='y', labelcolor='#888888')
    ax2.set_ylim(0, 7000)
    (lines1, labels1) = ax1.get_legend_handles_labels()
    (lines2, labels2) = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', framealpha=0.9, ncol=2)
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_xlim(-0.5, len(months) - 0.5)
    fig.tight_layout()
    save_rq1(fig, 'rq1_concentration')

def figure5() -> None:
    frame = pd.read_csv(DATA / 'scatter.csv.gz', float_precision='round_trip')
    thresholds = json.loads((DATA / 'inputs.json').read_text())['scatter']
    (download_p90, score_p90) = (thresholds['download_p90'], thresholds['score_p90'])
    visual = FIGURE_STYLE_CONTRACT['figure5']
    long_tail = frame.loc[frame['sample_order'] >= 0].sort_values('sample_order')
    others = frame.loc[frame['role'] != 'LT']
    fig, ax = plt.subplots(figsize=visual['figsize'])
    ax.scatter(long_tail['dl_plot'], long_tail['score_plot'], c=ROLE_COLORS['LT'], edgecolors='black', marker=visual['long_tail_marker'], s=visual['long_tail_marker_size'], alpha=0.52, linewidths=0.18, rasterized=True, label=ROLE_NAMES['LT'], zorder=3)
    marker_sizes = {'PL': 11, 'HR': 11, 'PR': 9}
    for role in ('HR', 'PR', 'PL'):
        subset = others.loc[others['role'] == role]
        style = {'c': 'white' if role == 'PL' else ROLE_COLORS[role], 'edgecolors': ROLE_COLORS[role] if role == 'PL' else 'black', 'linewidths': 0.7 if role == 'PL' else 0.3, 'alpha': 0.78 if role == 'PL' else 0.52, 'zorder': 4 if role == 'PL' else 2}
        ax.scatter(subset['dl_plot'], subset['score_plot'], marker=ROLE_MARKERS[role], s=marker_sizes[role], rasterized=True, label=ROLE_NAMES[role], **style)
    ax.axhline(score_p90, color='black', linestyle='--', linewidth=0.8, alpha=0.55)
    ax.axvline(download_p90, color='black', linestyle='--', linewidth=0.8, alpha=0.55)
    labels = {'HR': (0.03, 0.97, 'Hidden Roots\n(low usage, high reuse)', 'left', 'top'), 'PR': (0.97, 0.97, 'Popular Roots\n(high usage, high reuse)', 'right', 'top'), 'LT': (0.03, 0.03, 'Long Tail\n(low usage, low reuse)', 'left', 'bottom'), 'PL': (0.97, 0.03, 'Popular Leaves\n(high usage, low reuse)', 'right', 'bottom')}
    for (role, (x, y, label, ha, va)) in labels.items():
        ax.text(x, y, label, transform=ax.transAxes, fontsize=8, ha=ha, va=va, color=ROLE_COLORS[role], fontweight='bold', bbox={'boxstyle': 'round,pad=0.10', 'facecolor': 'white', 'edgecolor': 'none', 'alpha': 0.82})
    key_models = {'Qwen/Qwen3-4B-Instruct-2507': ('Qwen3-4B', (8, 10)), 'lerobot/smolvla_base': ('smolvla_base', (-48, 9)), 'Qwen/Qwen2.5-7B-Instruct': ('Qwen2.5-7B', (8, -13)), 'MuXodious/LFM2.5-1.2B-Thinking-absolute-heresy': ('LFM2.5-1.2B', (-52, 8)), 'YOYO-AI/Qwen3-30B-A3B-YOYO-V2': ('Qwen3-30B-YOYO', (8, -13))}
    for (model_id, (label, offset)) in key_models.items():
        selected = frame.loc[frame['model_id'] == model_id]
        if selected.empty:
            continue
        row = selected.iloc[0]
        ax.annotate(label, xy=(row['dl_plot'], row['score_plot']), xytext=offset, textcoords='offset points', fontsize=7, fontstyle='italic', bbox={'boxstyle': 'round,pad=0.15', 'facecolor': 'white', 'alpha': 0.8, 'edgecolor': 'none'}, arrowprops={'arrowstyle': '->', 'color': 'black', 'lw': 0.5})
    (x_low, x_high) = (download_p90 * 0.75, download_p90 * 3.4)
    (y_low, y_high) = (score_p90 * 0.75, score_p90 * 1.25)
    zoom = ax.inset_axes(visual['inset_bounds'])
    local = frame.loc[frame['dl_plot'].between(x_low, x_high) & frame['score_plot'].between(y_low, y_high)]
    for role in ('LT', 'HR', 'PR', 'PL'):
        subset = local.loc[local['role'] == role]
        style = {'LT': {'c': ROLE_COLORS[role], 'edgecolors': 'black', 's': 14, 'alpha': 0.6, 'linewidths': 0.24}, 'HR': {'c': ROLE_COLORS[role], 's': 8, 'alpha': 0.45, 'edgecolors': 'black', 'linewidths': 0.2}, 'PR': {'c': ROLE_COLORS[role], 's': 7, 'alpha': 0.45, 'edgecolors': 'black', 'linewidths': 0.2}, 'PL': {'facecolors': 'white', 'edgecolors': ROLE_COLORS[role], 's': 9, 'alpha': 0.8, 'linewidths': 0.55}}[role]
        zoom.scatter(subset['dl_plot'], subset['score_plot'], marker=ROLE_MARKERS[role], rasterized=True, **style)
    zoom.axhline(score_p90, color='black', linestyle='--', linewidth=0.6, alpha=0.55)
    zoom.axvline(download_p90, color='black', linestyle='--', linewidth=0.6, alpha=0.55)
    zoom.set_xscale('log')
    zoom.set_yscale('log')
    zoom.set_xlim(x_low, x_high)
    zoom.set_ylim(y_low, y_high)
    zoom.set_title('P90 boundary (zoom)', fontsize=6.5, pad=1.5)
    x_ticks = [download_p90 * 0.75, download_p90, download_p90 * 2.5]
    y_ticks = [score_p90 * 0.75, score_p90, score_p90 * 1.25]
    zoom.xaxis.set_major_locator(ticker.FixedLocator(x_ticks))
    zoom.xaxis.set_major_formatter(ticker.FixedFormatter([f'{value:.0f}' for value in x_ticks]))
    zoom.yaxis.set_major_locator(ticker.FixedLocator(y_ticks))
    zoom.yaxis.set_major_formatter(ticker.FixedFormatter([f'{value:.2f}' for value in y_ticks]))
    zoom.xaxis.set_minor_locator(ticker.NullLocator())
    zoom.yaxis.set_minor_locator(ticker.NullLocator())
    zoom.set_xlabel('Downloads (30-day)', fontsize=6, labelpad=1)
    zoom.set_ylabel('ModelRank', fontsize=6, labelpad=1)
    zoom.tick_params(axis='both', labelsize=5.5, length=2, pad=1)
    zoom.grid(alpha=0.15)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Downloads (30-day, log scale)')
    ax.set_ylabel('ModelRank Score (log scale)')
    ax.legend(loc=visual['legend_loc'], bbox_to_anchor=visual['legend_bbox'], ncol=visual['legend_columns'], framealpha=0.92, borderpad=0.4, labelspacing=0.35, handletextpad=0.45, markerscale=1.25, fontsize=7)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    save(fig, 'rq3_scatter')

def figure6(counts: Counter[tuple[str, str]]) -> None:
    visual = FIGURE_STYLE_CONTRACT['figure6']
    roles = list(visual['role_order'])
    role_labels = ['Popular\nRoots', 'Hidden\nRoots', 'Popular\nLeaves', 'Long\nTail']
    matrix = np.array([[counts[source, target] for target in roles] for source in roles])
    totals = matrix.sum(axis=1)
    rates = matrix / totals[:, None] * 100
    (fig, ax) = plt.subplots(figsize=visual['figsize'])
    image = ax.imshow(rates, cmap=visual['cmap'], aspect='auto')
    for i in range(4):
        for j in range(4):
            color = 'white' if rates[i, j] > 40 else 'black'
            if matrix[i, j] > 0:
                ax.text(j, i - 0.1, f'{int(matrix[i, j]):,}', ha='center', va='center', fontsize=7.2, fontweight='bold', color=color)
                ax.text(j, i + 0.14, f'({rates[i, j]:.1f}%)', ha='center', va='center', fontsize=6.3, color=color)
    ax.set_xticks(range(4), role_labels, fontsize=8)
    ax.set_yticks(range(4), role_labels, fontsize=8)
    ax.set_xlabel(visual['x_label'])
    ax.set_ylabel(visual['y_label'])
    colorbar = fig.colorbar(image, ax=ax, shrink=0.8)
    colorbar.set_label(visual['colorbar_label'], fontsize=8)
    fig.tight_layout()
    save(fig, 'rq4_transitions')

def compressed_positions(totals: dict[str, int]) -> dict[str, tuple[float, float]]:
    order = ['PR', 'HR', 'PL', 'LT']
    (gap, total_height, start_y) = (0.02, 0.85, 0.075)
    available = total_height - gap * (len(order) - 1)
    denom = sum((np.log1p(totals[role]) for role in order))
    y = start_y
    result = {}
    for role in order:
        height = available * np.log1p(totals[role]) / denom
        result[role] = (y, height)
        y += height + gap
    return result

def figure7(counts: Counter[tuple[str, str]]) -> None:
    visual = FIGURE_STYLE_CONTRACT['figure7']
    roles = ['PR', 'PL', 'HR', 'LT']
    order = list(visual['role_order'])
    outflow = {role: sum((counts[role, target] for target in roles)) for role in roles}
    inflow = {role: sum((counts[source, role] for source in roles)) for role in roles}
    left = compressed_positions(outflow)
    right = compressed_positions(inflow)
    flows = [(source, target, counts[source, target]) for source in roles for target in roles]
    (fig, ax) = plt.subplots(figsize=visual['figsize'])
    (left_x, right_x, width) = (0.15, 0.85, 0.04)
    for role in order:
        for (x, (y, height)) in ((left_x, left[role]), (right_x, right[role])):
            ax.add_patch(patches.FancyBboxPatch((x - width / 2, y), width, height, boxstyle='round,pad=0.003', facecolor=ROLE_COLORS[role], edgecolor='black', linewidth=1.0, alpha=0.9, hatch=ROLE_HATCHES[role]))
    left_offset = {role: left[role][0] for role in roles}
    right_offset = {role: right[role][0] for role in roles}
    centers = {}
    for (source, target, count) in sorted(flows, key=lambda row: (row[0] != row[1], -row[2])):
        lh = left[source][1] * count / outflow[source]
        rh = right[target][1] * count / inflow[target]
        (lb, rb) = (left_offset[source], right_offset[target])
        left_offset[source] += lh
        right_offset[target] += rh
        xs = np.linspace(left_x + width / 2, right_x - width / 2, 50)
        step = np.linspace(0, 1, 50)
        smooth = step ** 2 * (3 - 2 * step)
        top = lb + lh + (rb + rh - lb - lh) * smooth
        bottom = lb + (rb - lb) * smooth
        vertices = list(zip(xs, top)) + list(zip(xs[::-1], bottom[::-1]))
        ax.add_patch(patches.Polygon(vertices, facecolor=ROLE_COLORS[source], edgecolor='none', alpha=0.35 if source != target else 0.5))
        mid = len(xs) // 2
        centers[source, target] = (xs[mid], (top[mid] + bottom[mid]) / 2)
    short = {'PR': 'Popular\nRoots', 'PL': 'Popular\nLeaves', 'HR': 'Hidden\nRoots', 'LT': 'Long\nTail'}

    def compact_count(value: int) -> str:
        if value >= 1000000:
            return f'{value / 1000000:.2f}M'
        if value >= 1000:
            return f'{value / 1000:.1f}K'
        return str(value)
    for role in order:
        (y, height) = left[role]
        ax.text(left_x - 0.04, y + height / 2, short[role], ha='right', va='center', fontsize=10, fontweight='bold', color=ROLE_COLORS[role])
        stable = 100 * counts[role, role] / outflow[role]
        ax.text(left_x + 0.03, y + height / 2, f'{outflow[role]:,}\n({stable:.0f}% stable)', ha='left', va='center', fontsize=7.5, color='#444444')
    for (source, target, position) in (('HR', 'PR', (0.56, 0.26)), ('PL', 'LT', (0.58, 0.63)), ('LT', 'LT', (0.6, 0.88))):
        count = counts[source, target]
        rate = 100 * count / outflow[source]
        ax.annotate(f'{source}→{target}\n{compact_count(count)} ({rate:.1f}%)', xy=centers[source, target], xytext=position, fontsize=8, ha='left', va='center', bbox={'boxstyle': 'round,pad=0.2', 'facecolor': 'white', 'alpha': 0.86, 'edgecolor': '#bbbbbb'}, arrowprops={'arrowstyle': '->', 'color': '#666666', 'lw': 0.7})
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title('Role Transition Flows Between Consecutive Months\n(20-month aggregate; transition volume on a compressed node scale)', fontsize=12, fontweight='bold', pad=15)
    ax.text(left_x, 0.035, 'Month $t$', ha='center', va='top', fontsize=11, fontstyle='italic')
    ax.text(right_x, 0.035, 'Month $t{+}1$', ha='center', va='top', fontsize=11, fontstyle='italic')
    fig.tight_layout()
    save(fig, 'rq4_sankey')

def figure8(frame=None, model_styles=None) -> None:
    visual = FIGURE_STYLE_CONTRACT['figure8']
    assert set(frame['model_id']) == set(model_styles)
    months = sorted(frame['month'].unique())
    month_labels = [f'{month[2:4]}-{month[5:7]}' for month in months]
    x = {month: index for (index, month) in enumerate(months)}
    (fig, axes) = plt.subplots(2, 1, figsize=visual['figsize'], sharex=True)
    for (model_id, (label, color, marker)) in model_styles.items():
        subset = frame.loc[frame['model_id'] == model_id].sort_values('month')
        xs = [x[m] for m in subset['month']]
        axes[0].plot(xs, subset['signal'].clip(lower=1e-06), label=label, color=color, linestyle=visual['line_style'], marker=marker, markersize=4, linewidth=1.2)
        axes[1].plot(xs, subset['downloads'].clip(lower=1), label=label, color=color, linestyle=visual['line_style'], marker=marker, markersize=4, linewidth=1.2)
    axes[0].set_yscale('log')
    axes[1].set_yscale('log')
    axes[0].set_ylabel('ModelRank score')
    axes[1].set_ylabel('Downloads (30-day)')
    axes[1].set_ylim(bottom=1)
    ticks = list(range(0, len(months), 3))
    axes[1].set_xticks(ticks, [month_labels[i] for i in ticks], rotation=45, ha='right')
    for ax in axes:
        ax.grid(alpha=0.3)
    axes[0].legend(loc=visual['legend_loc'], framealpha=0.9, fontsize=7)
    axes[0].set_title(visual['panel_titles'][0], fontsize=9, loc='left')
    axes[1].set_title(visual['panel_titles'][1], fontsize=9, loc='left')
    fig.supxlabel('Month')
    fig.tight_layout()
    save(fig, 'rq4_trajectories')
# END EXTRACTED DRAWING FUNCTIONS

if __name__ == '__main__':
    main()
