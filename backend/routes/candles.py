import logging
from flask import Blueprint, jsonify, request
from services.candles.main import get_candles, VALID_RESOLUTIONS

logger     = logging.getLogger(__name__)
candles_bp = Blueprint('candles', __name__)

@candles_bp.route('/candles/<coin_id>', methods=['GET'])
def candles_route(coin_id):
    resolution = request.args.get('resolution', '1h')
    limit      = int(request.args.get('limit', 200))
    logger.info(f'GET /candles/{coin_id} res={resolution} limit={limit}')
    candles = get_candles(coin_id, resolution, limit)
    if candles is None:
        return jsonify({'error': 'Invalid resolution. Use: ' + str(list(VALID_RESOLUTIONS.keys()))}), 400
    if not candles:
        return jsonify({'error': f'No candle data for {coin_id} at {resolution}'}), 404
    return jsonify({'coin_id': coin_id, 'resolution': resolution, 'count': len(candles), 'candles': candles})
