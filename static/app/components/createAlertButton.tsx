import {
  addErrorMessage,
  addLoadingMessage,
  addSuccessMessage,
} from 'sentry/actionCreators/indicator';
import {navigateTo} from 'sentry/actionCreators/navigation';
import {hasEveryAccess} from 'sentry/components/acl/access';
import GuideAnchor from 'sentry/components/assistant/guideAnchor';
import type {ButtonProps} from 'sentry/components/button';
import {Button} from 'sentry/components/button';
import Link from 'sentry/components/links/link';
import {IconSiren} from 'sentry/icons';
import type {SVGIconProps} from 'sentry/icons/svgIcon';
import {t, tct} from 'sentry/locale';
import type {Organization, Project} from 'sentry/types';
import type EventView from 'sentry/utils/discover/eventView';
import useApi from 'sentry/utils/useApi';
import useRouter from 'sentry/utils/useRouter';
import withProjects from 'sentry/utils/withProjects';
import type {AlertType, AlertWizardAlertNames} from 'sentry/views/alerts/wizard/options';
import {
  AlertWizardRuleTemplates,
  DEFAULT_WIZARD_TEMPLATE,
} from 'sentry/views/alerts/wizard/options';

export type CreateAlertFromViewButtonProps = Omit<ButtonProps, 'aria-label'> & {
  /**
   * Discover query used to create the alert
   */
  eventView: EventView;
  organization: Organization;
  projects: Project[];
  alertType?: AlertType;
  className?: string;
  /**
   * Passed in value to override any metrics decision and switch back to transactions dataset.
   * We currently do a few checks on metrics data on performance pages and this passes the decision onward to alerts.
   */
  disableMetricDataset?: boolean;
  /**
   * Called when the user is redirected to the alert builder
   */
  onClick?: () => void;

  referrer?: string;
};

/**
 * Provide a button that can create an alert from an event view.
 * Emits incompatible query issues on click
 */
function CreateAlertFromViewButton({
  projects,
  eventView,
  organization,
  referrer,
  onClick,
  alertType,
  disableMetricDataset,
  ...buttonProps
}: CreateAlertFromViewButtonProps) {
  const project = projects.find(p => p.id === `${eventView.project[0]}`);
  const queryParams = eventView.generateQueryStringObject();
  if (queryParams.query?.includes(`project:${project?.slug}`)) {
    queryParams.query = (queryParams.query as string).replace(
      `project:${project?.slug}`,
      ''
    );
  }

  const alertTemplate = alertType
    ? AlertWizardRuleTemplates[alertType]
    : DEFAULT_WIZARD_TEMPLATE;

  const to = {
    pathname: `/organizations/${organization.slug}/alerts/new/metric/`,
    query: {
      ...queryParams,
      createFromDiscover: true,
      disableMetricDataset,
      referrer,
      ...alertTemplate,
      project: project?.slug,
      aggregate: queryParams.yAxis ?? alertTemplate.aggregate,
    },
  };

  const handleClick = () => {
    onClick?.();
  };

  return (
    <CreateAlertButton
      organization={organization}
      projects={projects}
      onClick={handleClick}
      to={to}
      aria-label={t('Create Alert')}
      {...buttonProps}
    />
  );
}

type CreateAlertButtonProps = {
  organization: Organization;
  projects: Project[];
  alertOption?: keyof typeof AlertWizardAlertNames;
  hideIcon?: boolean;
  iconProps?: SVGIconProps;
  /**
   * Callback when the button is clicked.
   * This is different from `onClick` which always overrides the default
   * behavior when the button was clicked.
   */
  onEnter?: () => void;
  projectSlug?: string;
  referrer?: string;
  showPermissionGuide?: boolean;
} & ButtonProps;

function CreateAlertButton({
  organization,
  projects,
  projectSlug,
  iconProps,
  referrer,
  hideIcon,
  showPermissionGuide,
  alertOption,
  onEnter,
  ...buttonProps
}: CreateAlertButtonProps) {
  const router = useRouter();
  const api = useApi();
  const createAlertUrl = (providedProj: string): string => {
    const params = new URLSearchParams();
    if (referrer) {
      params.append('referrer', referrer);
    }
    if (providedProj !== ':projectId') {
      params.append('project', providedProj);
    }
    if (alertOption) {
      params.append('alert_option', alertOption);
    }
    return `/organizations/${organization.slug}/alerts/wizard/?${params.toString()}`;
  };

  function handleClickWithoutProject(event: React.MouseEvent) {
    event.preventDefault();
    onEnter?.();

    navigateTo(createAlertUrl(':projectId'), router);
  }

  async function enableAlertsMemberWrite() {
    const settingsEndpoint = `/organizations/${organization.slug}/`;
    addLoadingMessage();
    try {
      await api.requestPromise(settingsEndpoint, {
        method: 'PUT',
        data: {
          alertsMemberWrite: true,
        },
      });
      addSuccessMessage(t('Successfully updated organization settings'));
    } catch (err) {
      addErrorMessage(t('Unable to update organization settings'));
    }
  }

  const permissionTooltipText = tct(
    'Ask your organization owner or manager to [settingsLink:enable alerts access] for you.',
    {settingsLink: <Link to={`/settings/${organization.slug}`} />}
  );

  const renderButton = (hasAccess: boolean) => (
    <Button
      disabled={!hasAccess}
      title={!hasAccess ? permissionTooltipText : undefined}
      icon={!hideIcon && <IconSiren {...iconProps} />}
      to={projectSlug ? createAlertUrl(projectSlug) : undefined}
      tooltipProps={{
        isHoverable: true,
        position: 'top',
        overlayStyle: {
          maxWidth: '270px',
        },
      }}
      onClick={projectSlug ? onEnter : handleClickWithoutProject}
      {...buttonProps}
    >
      {buttonProps.children ?? t('Create Alert')}
    </Button>
  );

  const showGuide = !organization.alertsMemberWrite && !!showPermissionGuide;
  const canCreateAlert =
    hasEveryAccess(['alerts:write'], {organization}) ||
    projects.some(p => hasEveryAccess(['alerts:write'], {project: p}));
  const hasOrgWrite = hasEveryAccess(['org:write'], {organization});

  return showGuide ? (
    <GuideAnchor
      target={hasOrgWrite ? 'alerts_write_owner' : 'alerts_write_member'}
      onFinish={hasOrgWrite ? enableAlertsMemberWrite : undefined}
    >
      {renderButton(canCreateAlert)}
    </GuideAnchor>
  ) : (
    renderButton(canCreateAlert)
  );
}

export {CreateAlertFromViewButton};
export default withProjects(CreateAlertButton);
