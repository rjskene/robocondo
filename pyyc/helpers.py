def line_plots(df, title, y_axis_label, width=450, height=300, excluded=[], months=None):
    x = df.index.name
    excluded.append(x)
    source = ColumnDataSource(df)

    plot = figure(title=title,
        x_axis_label="Date",
        x_axis_type="datetime",
        y_axis_label=y_axis_label,
        plot_width=width,
        plot_height=height
    )
    for i, col in enumerate(df.columns):
        if col not in excluded:
            plot.line(x=x, y=col, line_width=2, source=source, color=Category20c[20][i])

    script, div = components(plot)

    dct = {}
    dct["script"] = script
    dct["div"] = div

    return dct
