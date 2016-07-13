import base64
import uuid
from subprocess import Popen, PIPE

import boto3
from chalice import BadRequestError, Chalice


app = Chalice(app_name='thumbnail-service')
app.debug = True  # TODO: Disable on production

S3 = boto3.client('s3')
S3_BUCKET = ''  # TODO: Replace with valid bucket name


@app.route('/', methods=['POST'])
def index():
    body = app.current_request.json_body

    image = base64.b64decode(body['data'])
    format = {'jpg': 'jpeg', 'png': 'png'}[body.get('format', 'jpg').lower()]
    mode = {'max': '', 'min': '^', 'exact': '!'}[body.get('mode', 'max').lower()]
    width = int(body.get('width', 128))
    height = int(body.get('height', 128))

    cmd = [
        'convert',  # ImageMagick Convert
        '-',  # Read original picture from StdIn
        '-auto-orient',  # Detect picture orientation from metadata
        '-thumbnail', '{}x{}{}'.format(width, height, mode),  # Thumbnail size
        '-extent', '{}x{}'.format(width, height),  # Fill if original picture is smaller than thumbnail
        '-gravity', 'Center',  # Extend (fill) from the thumbnail middle
        '-unsharp',' 0x.5',  # Un-sharpen slightly to improve small thumbnails
        '-quality', '80%',  # Thumbnail JPG quality
        '{}:-'.format(format),  # Write thumbnail with `format` to StdOut
    ]

    p = Popen(cmd, stdout=PIPE, stdin=PIPE)
    thumbnail = p.communicate(input=image)[0]

    if not thumbnail:
        raise BadRequestError('Image format not supported')

    filename = '{}_{}x{}.{}'.format(uuid.uuid4(), width, height, format)
    S3.put_object(
        Bucket=S3_BUCKET,
        Key=filename,
        Body=thumbnail,
        ACL='public-read',
        ContentType='image/{}'.format(format),
    )

    return {
        'url': 'https://s3.amazonaws.com/{}/{}'.format(S3_BUCKET, filename)
    }
