"""
Alert API Routes
Provides REST endpoints for alert management and monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import Alert, Email, InboundEmailAnalysis, OutboundEmailAnalysis
from app.services.alerts.alert_service import AlertService
from app.services.alerts.alert_scheduler import alert_scheduler

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("/active")
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warning, info"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of alerts to return"),
    db: Session = Depends(get_db)
):
    """Get active (unresolved) alerts"""
    try:
        query = db.query(Alert).filter(Alert.resolved_at.is_(None))
        
        if severity:
            query = query.filter(Alert.severity == severity)
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)
        
        alerts = query.order_by(desc(Alert.triggered_at)).limit(limit).all()
        
        alert_data = []
        for alert in alerts:
            alert_dict = {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "email_id": alert.email_id,
                "priority_level": alert.priority_level,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "acknowledged_by": alert.acknowledged_by,
                "email_notification_sent": alert.email_notification_sent
            }
            alert_data.append(alert_dict)
        
        return {
            "success": True,
            "alerts": alert_data,
            "total": len(alert_data),
            "filters": {
                "severity": severity,
                "alert_type": alert_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")

@router.get("/dashboard")
async def get_alert_dashboard(db: Session = Depends(get_db)):
    """Get real-time alert dashboard data"""
    try:
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        # Active alerts by severity
        critical_count = db.query(Alert).filter(
            Alert.severity == "critical",
            Alert.resolved_at.is_(None)
        ).count()
        
        warning_count = db.query(Alert).filter(
            Alert.severity == "warning", 
            Alert.resolved_at.is_(None)
        ).count()
        
        info_count = db.query(Alert).filter(
            Alert.severity == "info",
            Alert.resolved_at.is_(None)
        ).count()
        
        # Recent alerts (last 24 hours)
        recent_alerts = db.query(Alert).filter(
            Alert.triggered_at >= last_24h
        ).order_by(desc(Alert.triggered_at)).limit(10).all()
        
        # Alert counts by type (last 24 hours)
        alert_type_counts = db.query(
            Alert.alert_type,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.triggered_at >= last_24h
        ).group_by(Alert.alert_type).all()
        
        # SLA breach summary
        sla_breaches = db.query(Alert).filter(
            Alert.alert_type == "sla_breach",
            Alert.triggered_at >= last_24h
        ).count()
        
        # Unacknowledged critical alerts
        unack_critical = db.query(Alert).filter(
            Alert.severity == "critical",
            Alert.acknowledged_at.is_(None),
            Alert.resolved_at.is_(None)
        ).count()
        
        return {
            "success": True,
            "dashboard": {
                "active_alerts": {
                    "critical": critical_count,
                    "warning": warning_count,
                    "info": info_count,
                    "total": critical_count + warning_count + info_count
                },
                "recent_alerts": [
                    {
                        "id": alert.id,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "title": alert.title,
                        "email_id": alert.email_id,
                        "triggered_at": alert.triggered_at.isoformat()
                    }
                    for alert in recent_alerts
                ],
                "alert_type_counts": {
                    alert_type: count for alert_type, count in alert_type_counts
                },
                "sla_breaches_24h": sla_breaches,
                "unacknowledged_critical": unack_critical,
                "last_updated": now.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query(..., description="Name or ID of person acknowledging the alert"),
    db: Session = Depends(get_db)
):
    """Acknowledge an alert"""
    try:
        success = await AlertService.acknowledge_alert(alert_id, acknowledged_by)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "success": True,
            "message": f"Alert {alert_id} acknowledged by {acknowledged_by}",
            "acknowledged_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")

@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark an alert as resolved"""
    try:
        success = await AlertService.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "success": True,
            "message": f"Alert {alert_id} resolved",
            "resolved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")

@router.get("/statistics")
async def get_alert_statistics(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get alert statistics for the specified period"""
    try:
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Total alerts in period
        total_alerts = db.query(Alert).filter(
            Alert.triggered_at >= start_date
        ).count()
        
        # Alerts by severity
        severity_counts = db.query(
            Alert.severity,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.triggered_at >= start_date
        ).group_by(Alert.severity).all()
        
        # Alerts by type
        type_counts = db.query(
            Alert.alert_type,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.triggered_at >= start_date
        ).group_by(Alert.alert_type).all()
        
        # Resolution statistics
        resolved_alerts = db.query(Alert).filter(
            Alert.triggered_at >= start_date,
            Alert.resolved_at.isnot(None)
        ).count()
        
        # Average resolution time (in hours)
        avg_resolution_time = db.query(
            func.avg(
                func.timestampdiff(
                    'SECOND',
                    Alert.triggered_at,
                    Alert.resolved_at
                ) / 3600.0
            )
        ).filter(
            Alert.triggered_at >= start_date,
            Alert.resolved_at.isnot(None)
        ).scalar()
        
        return {
            "success": True,
            "statistics": {
                "period_days": days,
                "total_alerts": total_alerts,
                "resolved_alerts": resolved_alerts,
                "resolution_rate": (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0,
                "avg_resolution_time_hours": round(avg_resolution_time or 0, 2),
                "severity_breakdown": {
                    severity: count for severity, count in severity_counts
                },
                "type_breakdown": {
                    alert_type: count for alert_type, count in type_counts
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get status of the alert scheduler"""
    try:
        status = alert_scheduler.get_job_status()
        return {
            "success": True,
            "scheduler": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")

@router.post("/scheduler/trigger/{check_type}")
async def trigger_manual_check(check_type: str):
    """Manually trigger a specific type of alert check"""
    try:
        valid_types = ["sla_breach", "aging_query", "factual_error", "negative_sentiment"]
        if check_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid check type. Must be one of: {', '.join(valid_types)}"
            )
        
        result = await alert_scheduler.trigger_manual_check(check_type)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Manual {result['type']} check completed",
                "alerts_created": result["alerts_created"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger manual check: {str(e)}")

@router.get("/types")
async def get_alert_types():
    """Get available alert types and their descriptions"""
    return {
        "success": True,
        "alert_types": {
            "sla_breach": {
                "description": "Query response time exceeded SLA threshold",
                "severity": "critical/warning",
                "threshold": "4h (high), 8h (medium), 24h (low)"
            },
            "aging_query": {
                "description": "Query aging beyond 24 hours without response",
                "severity": "warning",
                "threshold": "24 hours"
            },
            "factual_error": {
                "description": "Response contains factually incorrect information",
                "severity": "critical",
                "threshold": "Accuracy score < 0.7"
            },
            "negative_sentiment": {
                "description": "Response has negative or unprofessional tone",
                "severity": "warning",
                "threshold": "Sentiment score < 0.6"
            }
        }
    }
