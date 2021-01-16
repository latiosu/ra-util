import sys

import click
import yaml


@click.group()
def util():
    pass


def _load_yml(file):
    payload = yaml.load(file.read(), Loader=yaml.FullLoader)
    if 'Body' in payload:
        payload = payload['Body']
    return payload


def _to_dict(yml):
    return {str(entry['Id']): entry for entry in yml}


@util.command()
@click.option('--ids', is_flag=True, help='only output item ids')
@click.argument('src', type=click.File('r'))
@click.argument('dst', type=click.File('r'))
def difference(ids, src, dst):
    """Computes difference of DST minus SRC."""
    src_data = _load_yml(src)
    dst_data = _load_yml(dst)
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
    """Computes union of all files (duplicate ids overridden)."""
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
        data = _load_yml(f)
        for entry in data:
            # Adjust script format for clarity
            if 'Script' in entry:
                script = entry['Script'].replace('; ', ';\n').strip() + '\n'
                entry['Script'] = script
            result[entry['Id']] = entry
    if sort:
        result = list(sorted(result.values(), key=lambda v: v['Id']))
    click.echo(yaml.dump(result, sort_keys=False))


@util.command()
@click.option('-s', '--select',
              type=click.Choice([
                  'Id',
                  'Name',
                  'AegisName',
                  'Type',
                  'Slots',
                  'Script',
                ], case_sensitive=True),
              required=True,
              multiple=True,
              help='fields to output from HAYSTACK')
@click.option('--keep-blanks',
              is_flag=True,
              help='keep blank lines from NEEDLES')
@click.option('--ignore-missing',
              is_flag=True,
              help='skip output for missing NEEDLES')
@click.option('--format', '_format',
              help='format output fields, e.g. "ID:{} Slots:{}"')
@click.argument('needles', type=click.File('r'))
@click.argument('haystack', type=click.File('r'))
def find(select, keep_blanks, ignore_missing, _format, needles, haystack):
    """Finds NEEDLES in HAYSTACK and outputs desired value from HAYSTACK.

    NEEDLES is a line-separated list of item ids.
    HAYSTACK is an rathena item_db yaml.
    """
    if _format and len(select) != _format.count('{}'):
        raise click.UsageError('Mismatched number of arguments using format')
    result = list()
    data = _to_dict(_load_yml(haystack))
    for row in needles.read().splitlines():
        if row in data:
            entry = data[row]
            result.append([str(entry[s]) if s in entry else '' for s in select])
        elif not row and keep_blanks:
            result.append('')
        elif ignore_missing:
            continue
        else:
            result.append([row, 'MISSING'])
    for entry in result:
        if not entry:
            if keep_blanks:
                click.echo()
            else:
                continue
        elif _format:
            line = _format.format(*entry)
            click.echo(line.replace('\\t', '\t').replace('\\n', '\n'))
        else:
            click.echo('\t'.join(entry))


if __name__ == '__main__':
    util()