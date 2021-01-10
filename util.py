import sys

import click
import yaml


@click.group()
def util():
    pass


@util.command()
@click.option('--ids', is_flag=True, help='only output item ids')
@click.argument('src', type=click.File('r'))
@click.argument('dst', type=click.File('r'))
def difference(ids, src, dst):
    """Computes difference of DST minus SRC."""
    src_data = yaml.load(src.read(), Loader=yaml.FullLoader)
    dst_data = yaml.load(dst.read(), Loader=yaml.FullLoader)
    if 'Body' in src_data:
        src_data = src_data['Body']
    if 'Body' in dst_data:
        dst_data = dst_data['Body']
    if ids:
        src_ids = {v['Id'] for v in src_data}
        dst_ids = {v['Id'] for v in dst_data}
        click.echo('\n'.join(map(str, sorted(dst_ids - src_ids))))
    else:
        src_ids = {v['Id'] for v in src_data}
        diff = list()
        for entry in dst_data:
            if entry['Id'] not in src_ids:
                diff.append(entry)
        click.echo(yaml.dump(diff, sort_keys=False))


@util.command()
@click.option('--sort/--no-sort', default=True, help='sort result by id')
@click.argument('file', type=click.File('r'), nargs=-1)
def union(sort, file):
    """Computes union of all files (last occurrence takes precedence)."""
    # Refer to https://stackoverflow.com/a/15423007
    def should_use_block(value):
        for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
            if c in value:
                return True
        return False
    def my_represent_scalar(self, tag, value, style=None):
        if style is None:
            if should_use_block(value):
                style='|'
            else:
                style = self.default_style

        node = yaml.representer.ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node
    yaml.representer.BaseRepresenter.represent_scalar = my_represent_scalar

    result = dict()
    for f in file:
        data = yaml.load(f.read(), Loader=yaml.FullLoader)
        if 'Body' in data:
            data = data['Body']
        for entry in data:
            # Adjust script format for clarity
            if 'Script' in entry:
                script = entry['Script'].replace('; ', ';\n').strip() + '\n'
                entry['Script'] = script
            result[entry['Id']] = entry
    if sort:
        result = list(sorted(result.values(), key=lambda v: v['Id']))
    click.echo(yaml.dump(result, sort_keys=False))


if __name__ == "__main__":
    util()