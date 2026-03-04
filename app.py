import os
from copy import deepcopy
from pathlib import Path
from threading import Lock, Thread
from typing import Dict, Optional

from flask import Flask, render_template, jsonify, request, send_file

from logic.scripts.download_image import download_nature_image
from logic.scripts.download_quran_video import download_quran_video
from logic.scripts.extract_text_from_video import extract_text_from_video
from logic.scripts.create_final_video import create_final_video
from logic.scripts.post_to_instagram import post_to_instagram

app = Flask(__name__)

# Ensure required directories exist
os.makedirs('assets', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Store pipeline state
pipeline_state: Dict[str, Optional[str]] = {
    'image_path': None,
    'video_path': None,
    'video_title': None,
    'text_overlay_path': None,
    'final_video_path': None,
}

progress_lock = Lock()


def _new_progress_state():
    return {
        'active': False,
        'mode': None,
        'overall_percent': 0.0,
        'overall_message': '',
        'current_step': None,
        'step_order': [],
        'steps': {},
    }


progress_state = _new_progress_state()


def _recalculate_overall_locked():
    step_order = progress_state.get('step_order', [])
    if not step_order:
        progress_state['overall_percent'] = 0.0
        return

    total = len(step_order)
    score = 0.0

    for step in step_order:
        data = progress_state['steps'].get(step, {})
        status = data.get('status')
        if status in ('completed', 'skipped'):
            score += 1.0
        elif status == 'processing':
            score += max(0.0, min(100.0, float(data.get('progress', 0.0)))) / 100.0

    progress_state['overall_percent'] = round((score / total) * 100.0, 1)


def _reset_progress(mode, step_order):
    with progress_lock:
        progress_state.clear()
        progress_state.update(_new_progress_state())
        progress_state['active'] = True
        progress_state['mode'] = mode
        progress_state['step_order'] = list(step_order)
        progress_state['steps'] = {
            step: {
                'status': 'pending',
                'progress': 0.0,
                'message': '',
                'result': None,
            }
            for step in step_order
        }
        _recalculate_overall_locked()


def _set_step(step, *, status=None, progress=None, message=None, result=None):
    with progress_lock:
        if step not in progress_state.get('steps', {}):
            progress_state['steps'][step] = {
                'status': 'pending',
                'progress': 0.0,
                'message': '',
                'result': None,
            }
            progress_state['step_order'].append(step)

        data = progress_state['steps'][step]
        if status is not None:
            data['status'] = status
        if progress is not None:
            data['progress'] = round(max(0.0, min(100.0, float(progress))), 1)
        if message is not None:
            data['message'] = message
        if result is not None:
            data['result'] = result

        progress_state['current_step'] = step
        if message:
            progress_state['overall_message'] = message

        _recalculate_overall_locked()


def _finalize_progress(message='Done'):
    with progress_lock:
        progress_state['active'] = False
        progress_state['current_step'] = None
        progress_state['overall_message'] = message
        _recalculate_overall_locked()


@app.route('/')
def welcome():
    return render_template('main.html')


@app.route('/api/download-image', methods=['POST'])
def api_download_image():
    """Download a nature image from Unsplash"""
    try:
        data = request.get_json() or {}
        query = data.get('query', 'nature landscape')
        
        image_path = download_nature_image(
            output_path='assets/nature_image.jpg',
            query=query
        )
        
        if image_path:
            pipeline_state['image_path'] = image_path
            return jsonify({
                'success': True,
                'message': 'Image downloaded successfully',
                'path': image_path,
                'preview_url': f'/api/preview/image'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to download image'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/download-video', methods=['POST'])
def api_download_video():
    """Download a Quran video from YouTube"""
    try:
        data = request.get_json() or {}
        channel_url = data.get('channel_url', 'https://www.youtube.com/@Am9li9/videos')
        keyword = data.get('keyword', 'سورة')
        video_url = data.get('video_url')
        
        video_path, video_title, meta = download_quran_video(
            channel_url=channel_url,
            output_path='assets/quran_video.mp4',
            title_keyword=keyword,
            video_url=video_url,
        )
        
        if video_path:
            pipeline_state['video_path'] = video_path
            pipeline_state['video_title'] = video_title
            return jsonify({
                'success': True,
                'message': f'Video downloaded: {video_title}',
                'path': video_path,
                'title': video_title,
                'preview_url': f'/api/preview/video'
            })
        else:
            message = meta.get('message') if isinstance(meta, dict) else None
            return jsonify({
                'success': False,
                'message': message or 'Failed to download video',
                'duplicate': bool(meta.get('duplicate')) if isinstance(meta, dict) else False,
            }), 409 if isinstance(meta, dict) and meta.get('duplicate') else 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/extract-text', methods=['POST'])
def api_extract_text():
    """Extract transparent text overlay from video"""
    try:
        video_path = pipeline_state.get('video_path')
        
        if not video_path:
            return jsonify({
                'success': False,
                'message': 'No video available. Please download a video first.'
            }), 400
        
        text_overlay_path = extract_text_from_video(
            video_path=video_path,
            output_path='assets/quran_text_frame.mov'
        )
        
        if text_overlay_path:
            pipeline_state['text_overlay_path'] = text_overlay_path
            return jsonify({
                'success': True,
                'message': 'Text overlay extracted successfully',
                'path': text_overlay_path,
                'preview_url': f'/api/preview/overlay'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to extract text overlay'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/create-final', methods=['POST'])
def api_create_final():
    """Create final video with image background and text overlay"""
    try:
        image_path = pipeline_state.get('image_path')
        video_path = pipeline_state.get('video_path')
        text_overlay_path = pipeline_state.get('text_overlay_path')
        
        if not image_path:
            return jsonify({
                'success': False,
                'message': 'No image available. Please download an image first.'
            }), 400
        
        if not video_path:
            return jsonify({
                'success': False,
                'message': 'No video available. Please download a video first.'
            }), 400
        
        _reset_progress('create-final', ['final'])
        _set_step('final', status='processing', progress=0, message='Creating final video...')

        final_video_path = create_final_video(
            image_path=image_path,
            quran_video_path=video_path,
            text_frame_path=text_overlay_path,
            output_path='output/final_output.mp4',
            progress_callback=lambda percent, msg: _set_step('final', status='processing', progress=percent, message=msg),
        )
        
        if final_video_path:
            pipeline_state['final_video_path'] = final_video_path
            _set_step('final', status='completed', progress=100, message='Final video created successfully', result={
                'path': final_video_path,
                'preview_url': '/api/preview/final',
            })
            _finalize_progress('Final video created successfully')
            return jsonify({
                'success': True,
                'message': 'Final video created successfully',
                'path': final_video_path,
                'preview_url': f'/api/preview/final'
            })
        else:
            _set_step('final', status='error', message='Failed to create final video')
            _finalize_progress('Failed to create final video')
            return jsonify({
                'success': False,
                'message': 'Failed to create final video'
            }), 500
    except Exception as e:
        _set_step('final', status='error', message=f'Error: {str(e)}')
        _finalize_progress('Final video creation failed')
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/post-instagram', methods=['POST'])
def api_post_instagram():
    """Post final video to Instagram"""
    try:
        data = request.get_json() or {}
        caption = data.get('caption', '')
        
        final_video_path = pipeline_state.get('final_video_path')
        
        if not final_video_path:
            return jsonify({
                'success': False,
                'message': 'No final video available. Please create the final video first.'
            }), 400
        
        if not caption:
            video_title = pipeline_state.get('video_title', '')
            if video_title:
                caption = f"{video_title}\n\n#Quran #Islam #QuranVerses #DailyReminder #Faith #Peace"
            else:
                caption = "⚠️لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله⚠️\n\n#اكتب_شي_تؤجر_عليه #لاتنسى_ذكر_الله\n\n#الله #اكتب_شي_تؤجر_عليه #الله_أكبر #قران_كريم #لاتنسى_ذكر_الله #تلاوات #اللهم_امين"
        
        thumbnail_path = pipeline_state.get('image_path') or 'assets/nature_image.jpg'
        
        success = post_to_instagram(
            video_path=final_video_path,
            caption=caption,
            thumbnail_path=thumbnail_path
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Video posted to Instagram successfully! 🎉'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to post to Instagram'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


def _run_full_pipeline_bg(skip_text_overlay, auto_post, caption, channel_url, keyword, video_url):
    """Background task for full pipeline execution"""
    step_order = ['image', 'video', 'overlay', 'final'] + (['post'] if auto_post else [])
    _reset_progress('full-pipeline', step_order)
    
    try:
        # Step 1: Download image
        _set_step('image', status='processing', progress=0, message='Downloading image...')
        image_path = download_nature_image()
        if not image_path:
            _set_step('image', status='error', message='Failed to download image')
            _finalize_progress('Pipeline failed at image step')
            return
        pipeline_state['image_path'] = image_path
        image_result = {
            'step': 'image',
            'success': True,
            'message': 'Image downloaded successfully',
            'preview_url': '/api/preview/image',
        }
        _set_step('image', status='completed', progress=100, message=image_result['message'], result=image_result)
        
        # Step 2: Download video
        _set_step('video', status='processing', progress=0, message='Downloading video...')
        video_path, video_title, video_meta = download_quran_video(
            channel_url=channel_url,
            title_keyword=keyword,
            video_url=video_url,
        )
        if not video_path:
            video_error = video_meta.get('message') if isinstance(video_meta, dict) else 'Failed to download video'
            _set_step('video', status='error', message=video_error)
            _finalize_progress('Pipeline failed at video step')
            return
        pipeline_state['video_path'] = video_path
        pipeline_state['video_title'] = video_title
        video_result = {
            'step': 'video',
            'success': True,
            'message': f'Video downloaded: {video_title}',
            'preview_url': '/api/preview/video',
        }
        _set_step('video', status='completed', progress=100, message=video_result['message'], result=video_result)
        
        # Step 3: Extract text overlay (optional)
        text_overlay_path = None
        if not skip_text_overlay:
            _set_step('overlay', status='processing', progress=0, message='Extracting text overlay...')
            text_overlay_path = extract_text_from_video(video_path)
            if text_overlay_path:
                pipeline_state['text_overlay_path'] = text_overlay_path
                overlay_result = {
                    'step': 'overlay',
                    'success': True,
                    'message': 'Text overlay extracted successfully',
                    'preview_url': '/api/preview/overlay',
                }
                _set_step('overlay', status='completed', progress=100, message=overlay_result['message'], result=overlay_result)
            else:
                pipeline_state['text_overlay_path'] = None
                overlay_result = {
                    'step': 'overlay',
                    'success': False,
                    'message': 'Text overlay extraction failed. Continuing without overlay.',
                }
                _set_step('overlay', status='error', progress=100, message=overlay_result['message'], result=overlay_result)
                text_overlay_path = None
        else:
            overlay_result = {
                'step': 'overlay',
                'success': True,
                'message': 'Overlay step skipped by user option',
            }
            _set_step('overlay', status='skipped', progress=100, message=overlay_result['message'], result=overlay_result)
        
        # Step 4: Create final video
        _set_step('final', status='processing', progress=0, message='Creating final video...')
        final_video_path = create_final_video(
            image_path,
            video_path,
            text_overlay_path,
            progress_callback=lambda percent, msg: _set_step('final', status='processing', progress=percent, message=msg),
        )
        if not final_video_path:
            _set_step('final', status='error', message='Failed to create final video')
            _finalize_progress('Pipeline failed at final step')
            return
        pipeline_state['final_video_path'] = final_video_path
        final_result = {
            'step': 'final',
            'success': True,
            'message': 'Final video created successfully',
            'preview_url': '/api/preview/final',
        }
        _set_step('final', status='completed', progress=100, message=final_result['message'], result=final_result)
        
        # Step 5: Post to Instagram (optional)
        if auto_post:
            _set_step('post', status='processing', progress=0, message='Posting to Instagram...')
            if not caption:
                caption = f"{video_title}\n\n#Quran #Islam #QuranVerses" if video_title else "Daily Quran verse"
            
            success = post_to_instagram(final_video_path, caption, pipeline_state.get('image_path') or 'assets/nature_image.jpg')
            if not success:
                post_result = {
                    'step': 'post',
                    'success': False,
                    'message': 'Pipeline completed but posting failed',
                }
                _set_step('post', status='error', progress=100, message=post_result['message'], result=post_result)
                _finalize_progress('Pipeline completed with post failure')
                return
            post_result = {
                'step': 'post',
                'success': True,
                'message': 'Video posted to Instagram successfully',
            }
            _set_step('post', status='completed', progress=100, message=post_result['message'], result=post_result)
        
        _finalize_progress('Pipeline completed successfully')
    except Exception as e:
        print(f"Background pipeline error: {e}")
        _finalize_progress(f'Pipeline failed: {str(e)}')


@app.route('/api/run-full-pipeline', methods=['POST'])
def api_run_full_pipeline():
    """Run the complete pipeline from start to finish (non-blocking)"""
    try:
        data = request.get_json() or {}
        skip_text_overlay = data.get('skip_text_overlay', False)
        auto_post = data.get('auto_post', False)
        caption = data.get('caption', '')
        channel_url = data.get('channel_url', 'https://www.youtube.com/@Am9li9/videos')
        keyword = data.get('keyword', 'سورة')
        video_url = data.get('video_url')

        bg_thread = Thread(
            target=_run_full_pipeline_bg,
            args=(skip_text_overlay, auto_post, caption, channel_url, keyword, video_url),
            daemon=True
        )
        bg_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Pipeline started. Monitor progress via /api/progress endpoint.',
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/progress')
def api_progress():
    """Get live progress for long-running operations"""
    with progress_lock:
        snapshot = deepcopy(progress_state)
    return jsonify(snapshot)


@app.route('/api/preview/<media_type>')
def api_preview(media_type):
    """Serve media files for preview"""
    try:
        if media_type == 'image':
            path = pipeline_state.get('image_path', 'assets/nature_image.jpg')
        elif media_type == 'video':
            path = pipeline_state.get('video_path', 'assets/quran_video.mp4')
        elif media_type == 'overlay':
            path = pipeline_state.get('text_overlay_path', 'assets/quran_text_frame.mov')
        elif media_type == 'final':
            path = pipeline_state.get('final_video_path', 'output/final_output.mp4')
        else:
            return jsonify({'error': 'Invalid media type'}), 400
        
        if path and Path(path).exists():
            return send_file(path)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/state')
def api_state():
    """Get current pipeline state"""
    return jsonify({
        'has_image': pipeline_state.get('image_path') is not None,
        'has_video': pipeline_state.get('video_path') is not None,
        'has_overlay': pipeline_state.get('text_overlay_path') is not None,
        'has_final': pipeline_state.get('final_video_path') is not None,
        'video_title': pipeline_state.get('video_title'),
    })


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset pipeline state"""
    pipeline_state.clear()
    pipeline_state.update({
        'image_path': None,
        'video_path': None,
        'video_title': None,
        'text_overlay_path': None,
        'final_video_path': None,
    })
    return jsonify({'success': True, 'message': 'Pipeline state reset'})


@app.route('/api/reset-downloaded-videos', methods=['POST'])
def api_reset_downloaded_videos():
    """Clear downloaded video IDs tracking list"""
    try:
        downloaded_file = Path('assets/downloaded_videos.txt')
        downloaded_file.parent.mkdir(parents=True, exist_ok=True)
        downloaded_file.write_text('', encoding='utf-8')
        return jsonify({'success': True, 'message': 'Downloaded videos list has been reset'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500